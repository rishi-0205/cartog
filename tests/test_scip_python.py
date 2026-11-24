"""V3: `--python` must name a real interpreter, and be recorded as an absolute path.

The SCIP experiment in `docs/dev/VERIFICATION.md` shows that the indexer picks
its own interpreter when the flag is unusable, which is how foreign symbols
(`click 8.1.7` from a Windows Store Python) end up in the graph. Cartog can only
guarantee the flag was honoured if it refuses a path that does not exist and
pins the canonical path when it does.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from typer.testing import CliRunner

from cartog.cli import app

runner = CliRunner()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    (repo / "app.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    return repo


def _invoke(repo: Path, out: Path, *extra: str):
    return runner.invoke(
        app,
        ["analyze", str(repo), "--out", str(out), "--no-scip", "--no-render", *extra],
    )


def test_scip_python_flag_selects_interpreter(tmp_path):
    """A missing --python aborts before any run is written; a dotted path is recorded absolute."""
    repo = _repo(tmp_path)
    missing = tmp_path / "missing" / "python.exe"

    rejected = _invoke(repo, tmp_path / "out-missing", "--python", str(missing))

    assert rejected.exit_code == 2, rejected.stdout
    assert "no such interpreter" in " ".join(rejected.stdout.split()).lower()
    assert not (tmp_path / "out-missing").exists(), "a rejected run must not create output"

    dotted = (
        f"{Path(sys.executable).parent}{os.sep}.{os.sep}{Path(sys.executable).name}"
    )
    accepted = _invoke(repo, tmp_path / "out", "--python", dotted)

    assert accepted.exit_code == 0, accepted.stdout
    meta = json.loads((tmp_path / "out" / "meta.json").read_text(encoding="utf-8"))
    assert meta["tools"]["scip_python"] == str(Path(sys.executable).resolve())
