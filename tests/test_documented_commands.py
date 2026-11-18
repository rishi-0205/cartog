"""U6: the documented commands exist and the documented examples run.

The first test reads every ``cartog <word>`` mention in ``README.md`` and
``docs/USAGE.md`` and checks the word against the real command registry, so a
renamed or removed command cannot survive in the docs. The second test runs the
quick-start example from ``docs/USAGE.md`` against a temporary repository.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.main import get_command
from typer.testing import CliRunner

from cartog.cli import app

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = (REPO_ROOT / "README.md", REPO_ROOT / "docs" / "USAGE.md")
runner = CliRunner()

# `cartog <token>` where the token starts a word; options and paths are skipped.
COMMAND_MENTION = re.compile(r"\bcartog ([a-z][a-z0-9-]*)")


def test_documented_commands_exist():
    """Every command named in the docs is a registered command."""
    commands = set(get_command(app).commands)
    assert "analyze" in commands, "the unified command is not registered"

    seen: set[str] = set()
    for path in DOCS:
        assert path.is_file(), f"missing documented file: {path}"
        text = path.read_text(encoding="utf-8")
        seen |= set(COMMAND_MENTION.findall(text))

    unknown = sorted(seen - commands)
    assert not unknown, f"docs name commands that do not exist: {unknown}"
    assert "analyze" in seen, "docs never mention the unified command"
    for name in ("parse", "scip", "build", "map", "check", "flow", "view", "digest"):
        assert name in seen, f"docs dropped the stage command {name}"


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "example-project"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "app.py").write_text(
        "def helper():\n    return 1\n\ndef main():\n    return helper()\n",
        encoding="utf-8",
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text(
        "def test_main():\n    assert True\n", encoding="utf-8"
    )
    return repo


def test_documented_examples_run(tmp_path):
    """The quick-start example produces the documented tree, then checks it."""
    repo = _repo(tmp_path)
    out = tmp_path / "example-run"

    analyzed = runner.invoke(
        app,
        [
            "analyze",
            str(repo),
            "--out",
            str(out),
            "--no-scip",
            "--no-render",
            "--keep",
            "2",
        ],
    )
    assert analyzed.exit_code == 0, analyzed.stdout

    for rel in (
        "graph.json",
        "view/map.html",
        "diagrams/overview.mmd",
        "digest.md",
        "check.json",
        "meta.json",
        "logs/parse.log",
        ".complete",
    ):
        assert (out / rel).is_file(), f"missing documented output {rel}"

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "complete"
    assert meta["run_id"]
    assert meta["schema_version"] == "2.0.0"

    checked = runner.invoke(
        app, ["check", str(out / "graph.json"), "--no-scip"]
    )
    assert checked.exit_code == 0, checked.stdout

    rerun = runner.invoke(
        app,
        [
            "map",
            str(repo),
            "--out",
            str(tmp_path / "stage-run"),
            "--no-scip",
            "--include-tests",
        ],
    )
    assert rerun.exit_code == 0, rerun.stdout
    assert (tmp_path / "stage-run" / "overview.mmd").is_file()
