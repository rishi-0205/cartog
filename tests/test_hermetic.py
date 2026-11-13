"""Regression tests for F1/F2: the suite must be hermetic.

F1: `samples/` is gitignored, so a fresh clone has no sample repositories and
    sample-dependent tests must skip, not fail.
F2: sample-dependent tests and CLI runs must not write artifacts into the
    repository working tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import conftest
from conftest import requires_sample

REPO_ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _cartog_out_snapshot() -> dict[str, tuple[int, int]]:
    """Return ``{name: (size, mtime_ns)}`` for every file under ``cartog-out``."""
    out = REPO_ROOT / "cartog-out"
    if not out.is_dir():
        return {}
    return {
        p.relative_to(REPO_ROOT).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in out.rglob("*")
        if p.is_file()
    }


def _git_status() -> str:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


def test_samples_marker_skips_with_reason(tmp_path, monkeypatch):
    """The helper must skip (not fail) and name the fetch script in the reason."""
    monkeypatch.setattr(conftest, "SAMPLES_DIR", tmp_path / "empty-samples")

    with pytest.raises(pytest.skip.Exception) as excinfo:
        requires_sample("definitely-not-cloned")

    assert "scripts/fetch_samples.py" in str(excinfo.value)
    assert "definitely-not-cloned" in str(excinfo.value)


def test_sample_test_skips_in_a_tree_without_samples(tmp_path):
    """The E2E flow test must skip when its samples directory is absent.

    This is the fresh-clone scenario from F1: the test node runs in a separate
    process whose ``CARTOG_SAMPLES_DIR`` points at an empty directory.
    """
    node = f"{REPO_ROOT / 'tests' / 'test_cli.py'}::test_flow_demos_end_to_end"
    env = {**os.environ, "CARTOG_SAMPLES_DIR": str(tmp_path / "no-samples")}
    res = subprocess.run(
        [sys.executable, "-m", "pytest", node, "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    output = res.stdout + res.stderr
    assert res.returncode == 0, output
    assert "skipped" in output.lower(), output
    assert "failed" not in output.lower(), output


def test_flow_demos_write_only_tmp_path(tmp_path):
    """Running the E2E flow test must not touch the tree or `cartog-out` (F2)."""
    from test_cli import test_flow_demos_end_to_end

    before_files = _cartog_out_snapshot()
    before_status = _git_status()

    test_flow_demos_end_to_end(tmp_path)

    assert _cartog_out_snapshot() == before_files, "E2E flow test wrote into cartog-out/"
    assert _git_status() == before_status, "E2E flow test changed the worktree"


def test_suite_leaves_worktree_clean(tmp_path):
    """A representative CLI run writes only to its explicit `--out` directory."""
    from cartog.cli import app

    repo = tmp_path / "fixture_repo"
    repo.mkdir()
    (repo / "app.py").write_text(
        "def main():\n    return helper()\n\n\ndef helper():\n    return 1\n",
        encoding="utf-8",
    )
    out = tmp_path / "explicit-out"

    before_files = _cartog_out_snapshot()
    before_status = _git_status()

    res = runner.invoke(
        app,
        ["map", str(repo), "--out", str(out), "--no-scip"],
    )

    assert res.exit_code == 0, res.stdout
    assert (out / "graph.json").is_file()
    assert _cartog_out_snapshot() == before_files, "CLI wrote into the repo cartog-out/"
    assert _git_status() == before_status, "CLI changed the worktree"
