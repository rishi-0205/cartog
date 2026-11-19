"""Security-baseline tests (E3).

Each section of this file belongs to one E3 task and was added red-first:

* S1 — one subprocess runner, no direct ``subprocess`` use elsewhere.
* S2 — hostile canary repository never executes project code.
* S3 — map.html payload and DOM escaping.
* S4 — Mermaid label sanitisation.
* S5 — output path confinement and name sanitisation.
* S6 — terminal control-character stripping.
* S7 — vendored asset pins and tool version checks.
* S8 — configurable analysis limits.
* S9 — SECURITY.md links.
"""

from __future__ import annotations

import ast
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "cartog"


# --------------------------------------------------------------------------- S1


def _imports_subprocess(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "subprocess" for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            return True
    return False


def test_no_subprocess_outside_runner() -> None:
    """Only cartog/core/proc.py may import subprocess."""
    runner = PACKAGE_ROOT / "core" / "proc.py"
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted(PACKAGE_ROOT.rglob("*.py"))
        if path != runner and _imports_subprocess(path)
    ]
    assert offenders == [], f"subprocess imported outside cartog/core/proc.py: {offenders}"


def test_runner_rejects_unknown_binary() -> None:
    from cartog.core.proc import UnknownBinaryError, run

    with pytest.raises(UnknownBinaryError):
        run(["curl", "https://example.invalid"])


def test_runner_times_out() -> None:
    from cartog.core.proc import run

    started = time.perf_counter()
    result = run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        allow_python=True,
        timeout=0.2,
    )
    elapsed = time.perf_counter() - started
    assert result.timed_out is True
    assert result.returncode != 0
    assert elapsed < 4.0


def test_runner_caps_captured_output() -> None:
    from cartog.core.proc import run

    result = run(
        [sys.executable, "-c", "print('x' * 10000)"],
        allow_python=True,
        timeout=10,
        max_output_bytes=100,
    )
    assert result.returncode == 0
    assert len(result.stdout) <= 100
    assert result.truncated is True


def test_runner_env_allowlist_drops_secrets() -> None:
    from cartog.core.proc import filtered_env

    env = filtered_env({"PATH": "/bin", "CARTOG_SECRET_TOKEN": "shh", "NODE_OPTIONS": "-r x"})
    assert env["PATH"] == "/bin"
    assert env["NODE_OPTIONS"] == "-r x"
    assert "CARTOG_SECRET_TOKEN" not in env


def test_runner_never_uses_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    from cartog.core import proc

    seen: dict[str, object] = {}
    real_run = proc.subprocess.run

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(proc.subprocess, "run", spy)
    proc.run([sys.executable, "-c", "pass"], allow_python=True, timeout=10)
    assert seen.get("shell") is False
