"""U4: the unified `cartog analyze` command.

The command must write the complete layout before it reports a check failure, and
its exit code must follow the check result (0 pass, 1 fail, 0 skipped).
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cartog.cli import app

runner = CliRunner()

RUN_FILES = (
    "graph.json",
    "view/map.html",
    "digest.md",
    "check.json",
    "meta.json",
    "logs/parse.log",
    "logs/check.log",
    "stage/parse.json",
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


def _check_payload(status: str) -> dict:
    return {
        "status": status,
        "strict": False,
        "errors": [] if status == "pass" else ["forced failure"],
        "warnings": [],
        "cross_check": {"total": 0, "matched": 0, "explained": 0, "unexplained": 0},
        "scip": {"requested": False, "ran": False, "error": None},
    }


def test_unified_command_writes_outputs_before_check_failure(tmp_path, monkeypatch):
    """A failing check still leaves every output on disk, including meta.json."""
    from cartog.cli.commands import analyze as analyze_module

    def failing_check(graph, **kwargs):
        return _check_payload("fail"), False

    monkeypatch.setattr(analyze_module, "run_check", failing_check)
    out = tmp_path / "run"
    result = _invoke(_repo(tmp_path), out)

    assert result.exit_code == 1, result.stdout
    for rel in RUN_FILES:
        assert (out / rel).is_file(), f"missing {rel}"
    assert json.loads((out / "check.json").read_text(encoding="utf-8"))["status"] == "fail"
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "complete"
    assert meta["timings"]["total_ms"] >= 0


def test_unified_command_exit_code_follows_check(tmp_path, monkeypatch):
    """check pass -> 0, check fail -> 1, --no-check -> 0 with status skipped."""
    from cartog.cli.commands import analyze as analyze_module

    monkeypatch.setattr(
        analyze_module, "run_check", lambda *a, **k: (_check_payload("pass"), True)
    )
    passed = _invoke(_repo(tmp_path), tmp_path / "pass")
    assert passed.exit_code == 0, passed.stdout

    monkeypatch.setattr(
        analyze_module, "run_check", lambda *a, **k: (_check_payload("fail"), False)
    )
    failed = _invoke(_repo(tmp_path), tmp_path / "fail")
    assert failed.exit_code == 1, failed.stdout
    assert (tmp_path / "fail" / "meta.json").is_file()

    skipped = _invoke(_repo(tmp_path), tmp_path / "skipped", "--no-check")
    assert skipped.exit_code == 0, skipped.stdout
    payload = json.loads((tmp_path / "skipped" / "check.json").read_text(encoding="utf-8"))
    assert payload["status"] == "skipped"


def test_bare_cartog_prints_help_and_exits_zero():
    """A bare invocation is a help screen, not an implicit scan."""
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "analyze" in result.stdout


def test_unknown_top_level_token_is_a_usage_error():
    """A typo cannot start a long scan: unknown tokens exit 2."""
    result = runner.invoke(app, ["definitely-not-a-command"])
    assert result.exit_code == 2


def test_analyze_rejects_missing_target_and_bad_keep(tmp_path):
    """Input errors exit 2 before any run directory is created."""
    missing = runner.invoke(
        app, ["analyze", str(tmp_path / "nope"), "--out", str(tmp_path / "o")]
    )
    assert missing.exit_code == 2

    bad_keep = runner.invoke(
        app,
        ["analyze", str(_repo(tmp_path)), "--keep", "0", "--out", str(tmp_path / "k")],
    )
    assert bad_keep.exit_code == 2
    assert not (tmp_path / "k").exists()


def test_unified_command_real_run_writes_tree(tmp_path):
    """The real pipeline (no SCIP, no PNG) produces the documented tree."""
    out = tmp_path / "real"
    result = _invoke(_repo(tmp_path), out)
    assert result.exit_code == 0, result.stdout
    for rel in RUN_FILES:
        assert (out / rel).is_file(), f"missing {rel}"
    assert (out / ".complete").is_file()
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "complete"
    assert meta["target"]["languages"] == ["python"]
    assert meta["counts"]["files"] >= 1
