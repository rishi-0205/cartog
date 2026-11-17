"""Record and check the golden fingerprint of the Cartog pipeline.

Every E1 module move must leave the pipeline output unchanged. This script runs
the real CLI (``map`` -> ``digest`` -> ``view``) on a repository and records the
parts of the output that a refactor must not change:

* node and edge counts by kind,
* the digest size (characters and approximate tokens) and hash,
* the overview Mermaid hash,
* interactive-view element counts and roll-up statistics.

Usage:
    python scripts/golden.py --write [paths...]
    python scripts/golden.py --check [paths...]

The default paths are the three pinned samples (``samples/click``,
``samples/flask``, ``samples/ky``); each fingerprint is written to
``tests/golden/<repo name>.json``. ``--check`` recomputes the fingerprint and
reports a field-by-field difference count, exiting non-zero if anything moved.

Absolute paths are replaced with the repository name before hashing, so the
golden files are portable across machines and checkouts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
DEFAULT_REPOS = [
    REPO_ROOT / "samples" / "click",
    REPO_ROOT / "samples" / "flask",
    REPO_ROOT / "samples" / "ky",
]
VIEW_DATA_RE = re.compile(r"window\.CARTOG_VIEW_DATA = (\{.*\});")


class GoldenError(RuntimeError):
    """A pipeline run failed or produced an unreadable artefact."""


def _run(args: list[str]) -> None:
    proc = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-12:]
        raise GoldenError(
            f"{' '.join(args)} failed ({proc.returncode}):\n" + "\n".join(tail)
        )


def _normalise(text: str, repo: Path) -> str:
    """Replace absolute forms of ``repo`` with its name for portable hashing."""
    variants = {
        repo.as_posix(),
        str(repo),
        str(repo).replace("\\", "/"),
        repo.as_posix().replace("/", "\\"),
    }
    for value in sorted(variants, key=len, reverse=True):
        if value:
            text = text.replace(value, repo.name)
    return text


def _kind_counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        kind = str(item.get(key) or "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _viewer_stats(html: str) -> dict[str, int]:
    match = VIEW_DATA_RE.search(html)
    if match is None:
        raise GoldenError("map.html does not contain window.CARTOG_VIEW_DATA")
    payload = json.loads(match.group(1))
    elements = payload["elements"]
    nodes = [e for e in elements if "source" not in e["data"]]
    edges = [e for e in elements if "source" in e["data"]]
    meta = payload.get("meta", {})
    return {
        "elements": len(elements),
        "nodes": len(nodes),
        "edges": len(edges),
        "rolled_up_edges": int(meta.get("rolled_up_edges", 0)),
        "dropped_self_edges": int(meta.get("dropped_self_edges", 0)),
        "emitted_edges": int(meta.get("emitted_edges", 0)),
    }


def fingerprint(repo: Path) -> dict[str, Any]:
    """Run the pipeline on ``repo`` and return its golden fingerprint."""
    if not repo.is_dir():
        raise GoldenError(f"repository not found: {repo}")

    with tempfile.TemporaryDirectory(prefix="cartog-golden-") as tmp:
        out = Path(tmp) / "out"
        _run(
            [
                sys.executable,
                "-m",
                "cartog",
                "map",
                str(repo),
                "--out",
                str(out),
                "--no-scip",
                "--force",
            ]
        )

        graph_file = out / "graph.json"
        overview_file = out / "overview.mmd"
        if not graph_file.is_file() or not overview_file.is_file():
            raise GoldenError(f"pipeline did not write graph.json/overview.mmd for {repo}")

        graph = json.loads(graph_file.read_text(encoding="utf-8"))
        raw_nodes = graph.get("nodes", [])
        nodes = list(raw_nodes.values()) if isinstance(raw_nodes, dict) else list(raw_nodes)
        edges = list(graph.get("edges", []))
        mermaid = _normalise(overview_file.read_text(encoding="utf-8"), repo)

        digest_dir = Path(tmp) / "digest"
        _run(
            [
                sys.executable,
                "-m",
                "cartog",
                "digest",
                str(graph_file),
                "--out",
                str(digest_dir),
            ]
        )
        digest = _normalise((digest_dir / "digest.md").read_text(encoding="utf-8"), repo)

        view_dir = Path(tmp) / "view"
        _run(
            [
                sys.executable,
                "-m",
                "cartog",
                "view",
                str(graph_file),
                "--out",
                str(view_dir),
                "--no-open",
            ]
        )
        viewer = _viewer_stats((view_dir / "map.html").read_text(encoding="utf-8"))

    return {
        "repo": repo.name,
        "nodes": {"total": len(nodes), "by_kind": _kind_counts(nodes, "kind")},
        "edges": {"total": len(edges), "by_kind": _kind_counts(edges, "kind")},
        "digest": {
            "chars": len(digest),
            "approx_tokens": math.ceil(len(digest) / 4),
            "sha256": hashlib.sha256(digest.encode("utf-8")).hexdigest(),
        },
        "mermaid": {"overview_sha256": hashlib.sha256(mermaid.encode("utf-8")).hexdigest()},
        "viewer": viewer,
    }


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flat: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            flat.update(_flatten(child, child_prefix))
        return flat
    return {prefix: value}


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Return one message per differing field."""
    expected_flat = _flatten(expected)
    actual_flat = _flatten(actual)
    differences: list[str] = []
    for key in sorted(set(expected_flat) | set(actual_flat)):
        if expected_flat.get(key) != actual_flat.get(key):
            differences.append(
                f"  {key}: recorded={expected_flat.get(key)!r} actual={actual_flat.get(key)!r}"
            )
    return differences


def _write_one(repo: Path, golden_dir: Path) -> None:
    data = fingerprint(repo)
    golden_dir.mkdir(parents=True, exist_ok=True)
    path = golden_dir / f"{repo.name}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        shown = path.relative_to(REPO_ROOT)
    except ValueError:
        shown = path
    print(f"wrote {shown} ({data['nodes']['total']} nodes, {data['edges']['total']} edges)")


def _check_one(repo: Path, golden_dir: Path) -> int:
    path = golden_dir / f"{repo.name}.json"
    if not path.is_file():
        print(f"{repo.name}: missing golden file {path}")
        return 1
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = fingerprint(repo)
    differences = compare(expected, actual)
    if differences:
        print(f"{repo.name}: {len(differences)} difference(s)")
        for line in differences:
            print(line)
        return len(differences)
    print(f"{repo.name}: 0 differences")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="record the current output")
    mode.add_argument("--check", action="store_true", help="compare against the recorded output")
    parser.add_argument(
        "--golden-dir",
        default=str(DEFAULT_GOLDEN_DIR),
        help="directory holding <repo>.json (default: tests/golden)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[str(p) for p in DEFAULT_REPOS],
        help="repository paths (default: the three pinned samples)",
    )
    args = parser.parse_args(argv)

    golden_dir = Path(args.golden_dir)
    repo_paths = [Path(p).resolve() for p in args.paths]

    if args.write:
        for repo in repo_paths:
            _write_one(repo, golden_dir)
        return 0

    total = 0
    for repo in repo_paths:
        total += _check_one(repo, golden_dir)
    if total:
        noun = "difference" if total == 1 else "differences"
        print(f"{total} {noun}")
        return 1
    print("0 differences")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GoldenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
