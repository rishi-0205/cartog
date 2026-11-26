"""Materialize the pinned adversarial sample repositories.

``samples/`` is gitignored, so a fresh clone of Cartog has no sample repos.
The two torture samples are generated locally by scripts in ``scripts/`` —
there is no network clone. Integration tests skip when a sample is missing
(see ``tests/conftest.py``); run this script to generate them.

Usage:
    python scripts/fetch_samples.py                  # generate all pinned samples
    python scripts/fetch_samples.py cartog-torture-js  # generate one
    python scripts/fetch_samples.py --samples-dir D    # alternative destination
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = Path(__file__).resolve().parent / "samples.lock"


def generate_one(name: str, spec: dict[str, str], samples_dir: Path) -> str:
    """Generate one sample by running its pinned generator script."""
    dest = samples_dir / name
    if dest.is_dir() and any(dest.rglob("*")):
        count = sum(1 for _ in dest.rglob("*") if _.is_file())
        return f"{name}: already present ({count} files)"
    generator = REPO_ROOT / spec["generator"]
    if not generator.is_file():
        raise RuntimeError(f"missing generator: {generator}")
    samples_dir.mkdir(parents=True, exist_ok=True)
    print(f"{name}: generating via {spec['generator']}")
    proc = subprocess.run(
        [sys.executable, str(generator)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"generator failed: {(proc.stderr or proc.stdout).strip()}")
    return f"{name}: generated"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="sample names (default: all pinned)")
    parser.add_argument(
        "--samples-dir",
        default=str(REPO_ROOT / "samples"),
        help="destination directory (default: <repo>/samples)",
    )
    args = parser.parse_args(argv)

    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    samples: dict[str, dict[str, str]] = lock["samples"]
    names = args.names or sorted(samples)
    unknown = [n for n in names if n not in samples]
    if unknown:
        parser.error(f"unknown sample(s): {', '.join(unknown)}; known: {', '.join(sorted(samples))}")

    samples_dir = Path(args.samples_dir).resolve()
    failures = 0
    for name in names:
        try:
            print(generate_one(name, samples[name], samples_dir))
        except RuntimeError as exc:
            failures += 1
            print(f"error: {exc}", file=sys.stderr)

    if failures:
        print(f"\n{failures} sample(s) failed.", file=sys.stderr)
        return 1
    print(f"\n{len(names)} sample(s) ready under {samples_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
