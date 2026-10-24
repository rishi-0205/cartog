"""Basic CLI tests for Cartog."""

import subprocess
import sys
from typer.testing import CliRunner
from cartog.cli import app
from cartog import __version__

runner = CliRunner()


def test_cli_version():
    """Verify --version outputs the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help():
    """Verify --help displays available commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.stdout
    assert "parse" in result.stdout
    assert "map" in result.stdout


def test_cli_doctor():
    """Verify doctor command runs without error and inspects environment."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Cartog Doctor" in result.stdout
    assert "tree-sitter" in result.stdout


def test_cli_check_scip_failure_exits_nonzero_by_default(tmp_path):
    """Verify check command flags SCIP failure as an error and exits non-zero (code 1) by default."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "scip": {
                "ran": False,
                "indexer": "scip-python",
                "error": "scip-python failed pre-check, exit code 1\nSyntaxError: Invalid regular expression",
            },
        },
        "nodes": [],
        "edges": [],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    result = runner.invoke(app, ["check", str(graph_file)])
    assert result.exit_code == 1
    normalized_out = " ".join(result.stdout.split())
    assert "SCIP: FAILED (scip-python failed pre-check, exit code 1). No call edges in this graph." in normalized_out
    assert "FAIL" in normalized_out


def test_cli_check_scip_failure_opt_out_with_no_scip(tmp_path):
    """Verify check command exits 0 when --no-scip is passed to opt out of SCIP validation."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "scip": {
                "ran": False,
                "indexer": "scip-python",
                "error": "scip-python failed pre-check, exit code 1",
            },
        },
        "nodes": [],
        "edges": [],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    result = runner.invoke(app, ["check", str(graph_file), "--no-scip"])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_cli_check_scip_failure_strict(tmp_path):
    """Verify check command exits non-zero (code 1) when --strict is passed and SCIP failed."""
    import json
    graph_data = {
        "schema_version": "1.0.0",
        "meta": {
            "tool_version": "0.1.0",
            "scip": {
                "ran": False,
                "indexer": "scip-python",
                "error": "scip-python failed pre-check, exit code 1",
            },
        },
        "nodes": [],
        "edges": [],
        "skipped": [],
    }
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")

    result = runner.invoke(app, ["check", str(graph_file), "--strict"])
    assert result.exit_code == 1
    assert "SCIP: FAILED" in result.stdout


def test_cli_scip_loud_failure_output(tmp_path, monkeypatch):
    """Verify scip command outputs loud failure line when indexer fails."""
    from cartog.scip_pass import ScipIndexResult
    out_dir = tmp_path / "out"
    dummy_repo = tmp_path / "repo"
    dummy_repo.mkdir()

    monkeypatch.setattr(
        "cartog.cli._resolve_scip",
        lambda *args, **kwargs: ScipIndexResult(ran=False, indexer="scip-python", error="simulated failure"),
    )

    result = runner.invoke(app, ["scip", str(dummy_repo), "--out", str(out_dir)])
    normalized_out = " ".join(result.stdout.split())
    assert "SCIP: FAILED (simulated failure). No call edges in this graph." in normalized_out


