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
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cartog.cli import app

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "cartog"
HOSTILE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "hostile_repo"
CLI = CliRunner()


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


# --------------------------------------------------------------------------- S2


def _copy_hostile_repo(tmp_path: Path) -> Path:
    """Copy the hostile fixture and prove the canary is still armed."""
    assert HOSTILE_FIXTURE.is_dir(), f"missing hostile fixture: {HOSTILE_FIXTURE}"
    package = (HOSTILE_FIXTURE / "package.json").read_text(encoding="utf-8")
    setup = (HOSTILE_FIXTURE / "setup.py").read_text(encoding="utf-8")
    assert "HOSTILE_NPM_MARKER" in package, "the postinstall canary lost its marker"
    assert "HOSTILE_SETUP_MARKER" in setup, "the setup.py canary lost its marker"
    dest = tmp_path / "hostile_repo"
    shutil.copytree(HOSTILE_FIXTURE, dest)
    return dest


def _assert_marker_absent(tmp_path: Path, name: str) -> None:
    hits = [path for path in tmp_path.rglob(name) if path.is_file()]
    assert hits == [], f"hostile repository executed project code: {hits}"


def test_hostile_postinstall_never_runs(tmp_path: Path) -> None:
    """`npm install` is never run, so a postinstall marker can never appear."""
    repo = _copy_hostile_repo(tmp_path)
    result = CLI.invoke(
        app, ["analyze", str(repo), "--out", str(tmp_path / "out"), "--no-scip"]
    )
    assert result.exit_code == 0, result.stdout
    assert not (repo / "node_modules").exists()
    _assert_marker_absent(tmp_path, "HOSTILE_NPM_MARKER")


def test_hostile_setup_py_never_runs(tmp_path: Path) -> None:
    """`setup.py` is analysed as text, never imported or executed."""
    repo = _copy_hostile_repo(tmp_path)
    result = CLI.invoke(
        app, ["analyze", str(repo), "--out", str(tmp_path / "out"), "--no-scip"]
    )
    assert result.exit_code == 0, result.stdout
    _assert_marker_absent(tmp_path, "HOSTILE_SETUP_MARKER")


# --------------------------------------------------------------------------- S3

_HOSTILE_TEXT = "</script><script>alert('x')</script>&\u2028\u2029"


def _hostile_graph():
    """A graph whose names try to close the script tag and inject markup."""
    from cartog.core.model import Graph, Node

    hostile = _HOSTILE_TEXT
    graph = Graph()
    graph.meta = {"target_path": hostile, "cartog_version": "0.1.0"}
    graph.add_node(
        Node(
            id="fn_hostile",
            name=hostile,
            qualified_name=hostile,
            kind="function",
            path="evil.py",
        )
    )
    return graph


def test_html_payload_escapes_script_breakout() -> None:
    """Hostile names cannot close the inline script or add markup."""
    from cartog.render.export_html import generate_html_map

    html = generate_html_map(_hostile_graph())

    assert "</script><script>alert" not in html
    assert "\\u003c/script\\u003e" in html
    assert "\\u0026" in html
    payload_line = next(
        line for line in html.splitlines() if "window.CARTOG_VIEW_DATA" in line
    )
    assert "\\u2028" in payload_line
    assert "\\u2029" in payload_line
    assert "\u2028" not in payload_line
    assert "\u2029" not in payload_line
    parsed = json.loads(payload_line.split(" = ", 1)[1].rstrip(";"))
    assert parsed["meta"]["target_path"] == _HOSTILE_TEXT, (
        "escaping must preserve the value, not truncate it"
    )
    assert "&lt;/script&gt;" in html, "the header must HTML-escape the project name"


def test_html_viewer_uses_textcontent_only() -> None:
    """The viewer never builds DOM from strings."""
    js = (
        PACKAGE_ROOT / "render" / "assets" / "viewer.js"
    ).read_text(encoding="utf-8")
    forbidden = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(")
    hits = [word for word in forbidden if word in js]
    assert hits == [], f"viewer.js still builds DOM from strings: {hits}"
    assert "textContent" in js


def test_html_csp_blocks_network() -> None:
    """The CSP allows the bundled inline script and styles, and no origin."""
    from cartog.render.export_html import generate_html_map

    html = generate_html_map(_hostile_graph())
    match = re.search(
        r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', html
    )
    assert match, "map.html must declare a Content-Security-Policy"
    policy = match.group(1)
    assert "default-src 'none'" in policy
    for origin in ("http:", "https:", "ws:", "wss:", "*"):
        assert origin not in policy, f"CSP allows a network origin: {origin}"


# --------------------------------------------------------------------------- S4

_MERMAID_HOSTILE = (
    'x" [y] <b>hi</b> `code` %%{init: {"securityLevel":"loose"}}%%\nsecond & more'
)


def test_mermaid_label_rejects_directives() -> None:
    """A label cannot carry markup, a directive, a comment or a second line."""
    from cartog.render.export_mermaid import sanitize_label

    label = sanitize_label(_MERMAID_HOSTILE)

    assert "\n" not in label and "\r" not in label
    assert "%%" not in label, "a directive or comment survived"
    assert "<" not in label and ">" not in label
    assert "`" not in label
    assert '\\"' not in label, "Mermaid rejects backslash-quote inside a quoted label"
    assert "#quot;" in label
    assert "[y]" not in label, "brackets would close the node shape"


def test_mermaid_hostile_label_validates_with_mmdc(tmp_path: Path) -> None:
    """The generated diagram with a hostile name renders through mmdc."""
    from cartog.core.model import Graph, Node
    from cartog.render.export_mermaid import generate_overview_mermaid, render_mermaid

    if shutil.which("mmdc") is None:
        pytest.skip("mmdc (mermaid-cli) is not installed")

    graph = Graph()
    graph.meta = {"target_path": "hostile"}
    graph.add_node(
        Node(
            id="file_evil",
            name=_MERMAID_HOSTILE,
            qualified_name=_MERMAID_HOSTILE,
            kind="file",
            path="evil.py",
        )
    )
    mmd = generate_overview_mermaid(graph)
    assert "#quot;" in mmd, "the hostile file label is not in the diagram"
    assert "%%" not in mmd, "a comment or directive marker survived"

    mmd_file = tmp_path / "hostile.mmd"
    mmd_file.write_text(mmd, encoding="utf-8")
    ok, message = render_mermaid(mmd_file, tmp_path / "hostile.svg")
    assert ok, message
    assert (tmp_path / "hostile.svg").is_file()


# --------------------------------------------------------------------------- S5


def _make_junction(link: Path, target: Path) -> None:
    """Create a Windows junction (no privilege needed) or a POSIX symlink."""
    if sys.platform == "win32":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            pytest.skip(
                "cannot create a junction here: "
                + (completed.stderr or completed.stdout).strip()
            )
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - depends on host policy
        pytest.skip(f"cannot create a symlink here: {exc}")


def test_output_path_escape_rejected(tmp_path: Path) -> None:
    """A run-relative write may never leave the run directory."""
    from cartog.core.output import (
        OutputPathError,
        RunLayout,
        resolve_run_location,
    )

    out = tmp_path / "out"
    layout = RunLayout(resolve_run_location(tmp_path / "repo", out=out))

    for bad in ("../escaped.txt", "view/../../escaped.txt", str(tmp_path / "abs.txt")):
        with pytest.raises(OutputPathError):
            layout.write_text(bad, "x")

    assert not (tmp_path / "escaped.txt").exists()
    assert not (tmp_path / "abs.txt").exists()

    written = layout.write_text("view/map.html", "<html></html>")
    assert written == (out / "view" / "map.html").resolve()
    assert written.is_file()


def test_path_junction_outside_repo_rejected(tmp_path: Path) -> None:
    """A link inside the output root cannot be used to write outside it."""
    from cartog.core.output import (
        OutputPathError,
        RunLayout,
        resolve_run_location,
    )

    out = tmp_path / "out"
    out.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_junction(out / "view", outside)

    layout = RunLayout(resolve_run_location(tmp_path / "repo", out=out))
    with pytest.raises(OutputPathError):
        layout.write_text("view/pwned.txt", "x")
    assert not (outside / "pwned.txt").exists()


def test_path_junction_outside_repo_not_scanned(tmp_path: Path) -> None:
    """The walker never leaves the repository through a link."""
    from cartog.scan import walk_files

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.py").write_text("secret = 1\n", encoding="utf-8")
    _make_junction(repo / "linked", outside)

    result = walk_files(repo)
    paths = {info.path for info in result.files}
    assert "app.py" in paths
    assert not any(path.startswith("linked/") for path in paths)


def test_path_repo_name_sanitized() -> None:
    """Every hostile repository name becomes one safe folder component."""
    from cartog.core.output import MAX_PROJECT_NAME, sanitize_project_name

    assert sanitize_project_name("..") == "repo"
    assert sanitize_project_name("a/b\\c") == "a-b-c"
    assert sanitize_project_name("CON") == "_CON"
    assert sanitize_project_name("CON.txt").upper().startswith("_CON")
    assert sanitize_project_name("LPT1.log").upper().startswith("_LPT1")
    assert sanitize_project_name("name..") == "name"
    assert sanitize_project_name("name  ") == "name"
    assert sanitize_project_name("") == "repo"

    long_name = sanitize_project_name("x" * 100)
    assert len(long_name) <= MAX_PROJECT_NAME
    assert not long_name.endswith((".", " "))
    assert "/" not in long_name and "\\" not in long_name
    assert ":" not in long_name
