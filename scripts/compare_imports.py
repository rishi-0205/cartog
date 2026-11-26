"""Compare cartog's file-level import edges with an independent tool (E4/V4).

Cartog resolves imports itself (tree-sitter specifiers, then per-language
resolution in ``cartog/graph/merge.py``). This script checks that work against
tools that were written by someone else:

* ``grimp`` (Python) — builds a static import graph of a package;
* ``madge`` (JavaScript/TypeScript) — resolves module dependencies.

Both sides are reduced to the same shape, a set of ``(importer file, imported
file)`` pairs relative to the repository root, and scored:

    precision = |ours & theirs| / |ours|
    recall    = |ours & theirs| / |theirs|

Edges only cartog reports are listed as ``only_ours`` (precision losses: noise,
or real imports the reference tool misses); edges only the reference tool
reports are ``only_theirs`` (recall losses).

Usage:
    python scripts/compare_imports.py samples/click
    python scripts/compare_imports.py samples/flask --tool grimp
    python scripts/compare_imports.py samples/ky --tool madge --json

Notes:
* Only *internal* imports are compared: cartog's ``imports`` edges between two
  files in the repository. External packages and stdlib imports are neither
  reported by grimp (``include_external_packages=False``) nor meaningful for
  madge.
* grimp indexes one importable package, so for Python repositories the
  comparison is restricted to files that belong to that package. Tests,
  examples and scripts are outside it and are ignored on both sides.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
JS_EXTENSIONS = ("js", "jsx", "ts", "tsx")
PY_ROOTS = ("", "src", "lib")


def _run(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a tool from PATH, going through cmd.exe for Windows ``.cmd`` shims."""
    found = shutil.which(argv[0])
    if found is None:
        raise SystemExit(f"required tool not found on PATH: {argv[0]}")
    command = [found, *argv[1:]]
    if sys.platform == "win32" and found.lower().endswith((".cmd", ".bat")):
        command = ["cmd", "/c", *command]
    return subprocess.run(
        command, cwd=str(cwd) if cwd else None, capture_output=True, text=True
    )


def cartog_edges(repo: Path) -> set[tuple[str, str]]:
    """Run cartog without SCIP and return its file-to-file ``imports`` pairs."""
    repo = repo.resolve()
    with tempfile.TemporaryDirectory(prefix="cartog-compare-") as tmp:
        result = _run(
            [
                sys.executable,
                "-m",
                "cartog",
                "analyze",
                str(repo),
                "--out",
                tmp,
                "--no-scip",
                "--no-render",
                "--no-digest",
                "--no-view",
                "--no-check",
            ]
        )
        graph_file = Path(tmp) / "graph.json"
        if not graph_file.is_file():
            raise SystemExit(
                "cartog produced no graph:\n" + (result.stdout or "") + (result.stderr or "")
            )
        graph = json.loads(graph_file.read_text(encoding="utf-8"))
    paths = {node["id"]: node.get("path") for node in graph["nodes"]}
    return {
        (paths[edge["source"]], paths[edge["target"]])
        for edge in graph["edges"]
        if edge["kind"] == "imports"
        and paths.get(edge["source"])
        and paths.get(edge["target"])
    }


def _python_packages(repo: Path) -> list[tuple[str, str]]:
    """Return ``(root, package)`` pairs for importable top-level packages."""
    found: list[tuple[str, str]] = []
    for root in PY_ROOTS:
        base = repo / root if root else repo
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file():
                found.append((root, child.name))
    return found


def _module_file(repo: Path, root: str, module: str) -> Path | None:
    """Map ``pkg.mod`` to its file inside ``root`` (module) or ``__init__`` (package)."""
    base = repo / root if root else repo
    parts = module.split(".")
    module_file = base.joinpath(*parts).with_suffix(".py")
    if module_file.is_file():
        return module_file
    package_file = base.joinpath(*parts) / "__init__.py"
    if package_file.is_file():
        return package_file
    return None


def grimp_edges(repo: Path) -> set[tuple[str, str]]:
    """Return grimp's import pairs for every importable package in ``repo``."""
    return _grimp_graph(repo)[0]


def _grimp_graph(repo: Path) -> tuple[set[tuple[str, str]], set[str]]:
    """Return grimp's import pairs and the set of files it indexed."""
    import grimp

    repo = repo.resolve()
    packages = _python_packages(repo)
    if not packages:
        raise SystemExit(f"no importable package found under {repo}")

    roots = sorted({root for root, _ in packages})
    for root in roots:
        sys.path.insert(0, str(repo / root if root else repo))
    try:
        graph = grimp.build_graph(
            *[package for _, package in packages], cache_dir=None
        )
        modules = set(graph.modules)
        indexed: set[str] = set()
        pairs: set[tuple[str, str]] = set()
        for module in modules:
            target_file = _module_file(repo, roots[0], module)
            if target_file is None:
                continue
            indexed.add(target_file.relative_to(repo).as_posix())
        for module in modules:
            importer = _module_file(repo, roots[0], module)
            if importer is None:
                continue
            for imported in graph.find_modules_directly_imported_by(module):
                if imported not in modules:
                    continue
                target = _module_file(repo, roots[0], imported)
                if target is None:
                    continue
                pairs.add(
                    (
                        importer.relative_to(repo).as_posix(),
                        target.relative_to(repo).as_posix(),
                    )
                )
        return pairs, indexed
    finally:
        for root in roots:
            try:
                sys.path.remove(str(repo / root if root else repo))
            except ValueError:
                pass


def _js_source_dir(repo: Path) -> Path:
    """Pick the directory madge should scan: ``source/`` when present."""
    source = repo / "source"
    return source if source.is_dir() else repo


def madge_edges(repo: Path, *, source_dir: str | None = None) -> set[tuple[str, str]]:
    """Return madge's dependency pairs, keyed by repository-relative paths."""
    repo = repo.resolve()
    scan_dir = (repo / source_dir) if source_dir else _js_source_dir(repo)
    result = _run(
        [
            "madge",
            "--json",
            "--extensions",
            ",".join(JS_EXTENSIONS),
            str(scan_dir),
        ]
    )
    if result.returncode != 0:
        raise SystemExit("madge failed:\n" + (result.stdout or "") + (result.stderr or ""))
    payload = json.loads(result.stdout or "{}")
    prefix = scan_dir.relative_to(repo).as_posix()
    pairs: set[tuple[str, str]] = set()
    for importer, imported in payload.items():
        source = importer if prefix == "." else f"{prefix}/{importer}"
        for target in imported:
            pairs.add((source, target if prefix == "." else f"{prefix}/{target}"))
    return pairs


def compare_edges(
    ours: set[tuple[str, str]], theirs: set[tuple[str, str]]
) -> dict[str, Any]:
    """Score two edge sets; ``None`` ratios mean the denominator was empty."""
    shared = ours & theirs
    return {
        "ours": len(ours),
        "theirs": len(theirs),
        "true_positives": len(shared),
        "precision": (len(shared) / len(ours)) if ours else None,
        "recall": (len(shared) / len(theirs)) if theirs else None,
        "only_ours": sorted(ours - theirs),
        "only_theirs": sorted(theirs - ours),
    }


def _format_ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def report(repo: Path, tool: str, *, limit: int = 15) -> dict[str, Any]:
    """Build the comparison report for one repository and one reference tool.

    Both sides are restricted to the files the reference tool indexed, so the
    ratios describe the same universe. Pairs outside it are counted as
    ``excluded`` and explained in ``VERIFICATION.md``.
    """
    ours = cartog_edges(repo)
    if tool == "grimp":
        theirs, universe = _grimp_graph(repo)
    elif tool == "madge":
        scan_dir = _js_source_dir(repo)
        theirs = madge_edges(repo)
        universe = {
            path.relative_to(repo).as_posix()
            for path in scan_dir.rglob("*")
            if path.is_file() and path.suffix.lstrip(".") in JS_EXTENSIONS
        }
    else:  # pragma: no cover - argparse constrains this
        raise SystemExit(f"unknown tool: {tool}")

    comparable = {(a, b) for a, b in ours if a in universe and b in universe}
    data = compare_edges(comparable, theirs)
    data["tool"] = tool
    data["repo"] = repo.name
    data["excluded"] = len(ours) - len(comparable)
    data["only_ours_count"] = len(data["only_ours"])
    data["only_theirs_count"] = len(data["only_theirs"])
    data["only_ours"] = data["only_ours"][:limit]
    data["only_theirs"] = data["only_theirs"][:limit]
    return data


def _detect_tool(repo: Path) -> str:
    if _python_packages(repo):
        return "grimp"
    if any(p.suffix.lstrip(".") in JS_EXTENSIONS for p in repo.rglob("*") if p.is_file()):
        return "madge"
    raise SystemExit(f"cannot tell how to import-check {repo}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", type=Path, help="repository to compare")
    parser.add_argument(
        "--tool", choices=("auto", "grimp", "madge"), default="auto", help="reference tool"
    )
    parser.add_argument("--json", action="store_true", help="print the raw report")
    parser.add_argument("--limit", type=int, default=15, help="discrepancies to print")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    if not repo.is_dir():
        raise SystemExit(f"not a directory: {repo}")
    tool = _detect_tool(repo) if args.tool == "auto" else args.tool
    data = report(repo, tool, limit=args.limit)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print(f"{data['repo']} vs {data['tool']}")
    print(f"  cartog edges : {data['ours']}")
    print(f"  {data['tool']:<12} : {data['theirs']}")
    print(f"  shared       : {data['true_positives']}")
    print(f"  precision    : {_format_ratio(data['precision'])}")
    print(f"  recall       : {_format_ratio(data['recall'])}")
    print(f"  excluded     : {data['excluded']} (outside the files {data['tool']} indexes)")
    if data["only_ours"]:
        print(f"  only cartog ({data['only_ours_count']}):")
        for source, target in data["only_ours"]:
            print(f"    {source} -> {target}")
    if data["only_theirs"]:
        print(f"  only {data['tool']} ({data['only_theirs_count']}):")
        for source, target in data["only_theirs"]:
            print(f"    {source} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
