"""V1: `--timings` records per-stage wall time and peak memory in meta.json.

The timings are forensic data for one run. They must never leak into the
deterministic artefacts (graph, diagrams, digest, view, check) that the golden
fingerprint pins.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cartog.cli import app

runner = CliRunner()

STAGE_KEYS = (
    "parse_ms",
    "scip_ms",
    "build_ms",
    "diagrams_ms",
    "digest_ms",
    "view_ms",
    "check_ms",
)

DETERMINISTIC_FILES = (
    "graph.json",
    "digest.md",
    "check.json",
    "view/map.html",
    "view/overview.html",
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    (repo / "app.py").write_text(
        "def helper():\n    return 1\n\ndef main():\n    return helper()\n",
        encoding="utf-8",
    )
    return repo


def _invoke(repo: Path, out: Path, *extra: str):
    return runner.invoke(
        app,
        ["analyze", str(repo), "--out", str(out), "--no-scip", "--no-render", *extra],
    )


def _meta(out: Path) -> dict:
    return json.loads((out / "meta.json").read_text(encoding="utf-8"))


def test_meta_json_records_stage_timings(tmp_path):
    """meta.json carries one duration per stage plus peak memory."""
    repo = _repo(tmp_path)
    out = tmp_path / "out"

    result = _invoke(repo, out, "--timings")

    assert result.exit_code == 0, result.stdout
    timings = _meta(out)["timings"]
    assert "total_ms" in timings
    for key in STAGE_KEYS:
        assert key in timings, f"missing {key}"
        assert isinstance(timings[key], (int, float))
        assert timings[key] >= 0
    assert timings["peak_memory_mb"] > 0


def test_timings_do_not_change_goldens(tmp_path):
    """The same run with and without --timings produces identical artefacts."""
    repo = _repo(tmp_path)
    plain = tmp_path / "plain"
    timed = tmp_path / "timed"

    plain_result = _invoke(repo, plain)
    timed_result = _invoke(repo, timed, "--timings")
    assert plain_result.exit_code == 0, plain_result.stdout
    assert timed_result.exit_code == 0, timed_result.stdout

    for relative in DETERMINISTIC_FILES:
        assert (plain / relative).read_bytes() == (timed / relative).read_bytes(), (
            f"{relative} changed when --timings was enabled"
        )

    plain_timings = _meta(plain)["timings"]
    timed_timings = _meta(timed)["timings"]
    assert "peak_memory_mb" not in plain_timings
    assert "peak_memory_mb" in timed_timings
