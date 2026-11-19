"""U5: every stage command survives, and the consolidated flag names work.

No command is removed in E2. `--include-tests` / `--include-examples` become the
canonical spellings on `map`; the comma-separated `--include` list and
`--no-cache` stay accepted as compatibility aliases.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cartog.cli import app

runner = CliRunner()

STAGE_COMMANDS = (
    "analyze",
    "parse",
    "scip",
    "build",
    "map",
    "check",
    "flow",
    "view",
    "digest",
    "query",
    "doctor",
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "app.py").write_text(
        "def main():\n    return helper()\n\ndef helper():\n    return 1\n",
        encoding="utf-8",
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text(
        "def test_main():\n    assert True\n",
        encoding="utf-8",
    )
    return repo


def test_all_legacy_commands_still_invokable():
    """The root help lists every command, and every command has help."""
    root = runner.invoke(app, ["--help"])
    assert root.exit_code == 0, root.stdout
    for name in STAGE_COMMANDS:
        assert name in root.stdout, f"{name} missing from root help"
        helped = runner.invoke(app, [name, "--help"])
        assert helped.exit_code == 0, f"{name} --help failed: {helped.stdout}"


def test_consolidated_flags_aliases(tmp_path):
    """`--include-tests` expands tests; legacy `--include` and `--no-cache` work."""
    repo = _repo(tmp_path)
    plain = runner.invoke(
        app, ["map", str(repo), "--out", str(tmp_path / "plain"), "--no-scip"]
    )
    assert plain.exit_code == 0, plain.stdout
    plain_mmd = (tmp_path / "plain" / "overview.mmd").read_text(encoding="utf-8")
    assert "test_app" not in plain_mmd

    included = runner.invoke(
        app,
        [
            "map",
            str(repo),
            "--out",
            str(tmp_path / "included"),
            "--no-scip",
            "--include-tests",
            "--no-cache",
        ],
    )
    assert included.exit_code == 0, included.stdout
    included_mmd = (tmp_path / "included" / "overview.mmd").read_text(encoding="utf-8")
    assert "test_app" in included_mmd

    legacy = runner.invoke(
        app,
        [
            "map",
            str(repo),
            "--out",
            str(tmp_path / "legacy"),
            "--no-scip",
            "--include",
            "tests,examples",
        ],
    )
    assert legacy.exit_code == 0, legacy.stdout
    legacy_mmd = (tmp_path / "legacy" / "overview.mmd").read_text(encoding="utf-8")
    assert "test_app" in legacy_mmd
