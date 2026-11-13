"""Clone the pinned sample repositories used by integration tests.

``samples/`` is gitignored, so a fresh clone of Cartog has no real-world
repositories. Integration tests skip when a sample is missing (see
``tests/conftest.py``); run this script to enable them.

Usage:
    python scripts/fetch_samples.py                  # fetch every pinned sample
    python scripts/fetch_samples.py click flask      # fetch selected samples
    python scripts/fetch_samples.py --samples-dir D  # alternative destination

Each repository is cloned from ``scripts/samples.lock`` and checked out at the
recorded commit. Existing directories are verified but never modified; if the
checkout differs from the lock the script fails and tells you why.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = Path(__file__).resolve().parent / "samples.lock"


def run_git(*args: str, cwd: Path | None = None) -> str:
    """Run git with a list of arguments (never a shell string)."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} failed ({proc.returncode}): {detail}")
    return proc.stdout.strip()


def head_sha(dest: Path) -> str | None:
    if not (dest / ".git").exists():
        return None
    try:
        return run_git("rev-parse", "HEAD", cwd=dest)
    except RuntimeError:
        return None


def fetch_one(name: str, spec: dict[str, str], samples_dir: Path) -> str:
    """Fetch one sample and return a one-line status."""
    dest = samples_dir / name
    expected = spec["sha"]

    if dest.exists():
        actual = head_sha(dest)
        if actual is None:
            raise RuntimeError(
                f"{dest} exists but is not a git checkout; move it away and rerun"
            )
        if actual != expected:
            raise RuntimeError(
                f"{dest} is at {actual}, lock expects {expected}; "
                "move it away and rerun (the script never rewrites a checkout)"
            )
        return f"{name}: already at {expected[:12]}"

    samples_dir.mkdir(parents=True, exist_ok=True)
    print(f"{name}: cloning {spec['url']} -> {dest}")
    run_git("clone", "--no-checkout", spec["url"], str(dest))
    run_git("checkout", "--detach", expected, cwd=dest)

    actual = head_sha(dest)
    if actual != expected:
        raise RuntimeError(f"{name}: checkout ended at {actual}, expected {expected}")
    return f"{name}: checked out {expected[:12]}"


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
            print(fetch_one(name, samples[name], samples_dir))
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
