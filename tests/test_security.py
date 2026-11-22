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
import tomllib
from importlib.metadata import version as dist_version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cartog.cli import app
from cartog.core.toolchain import parse_version

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


# --------------------------------------------------------------------------- S6


def test_console_strips_ansi_and_controls() -> None:
    """Terminal output cannot carry escape sequences or C0/C1 controls."""
    from io import StringIO

    from cartog.cli.shared import SanitizingConsole, console
    from cartog.core.text import sanitize_console_text

    assert isinstance(console, SanitizingConsole), (
        "the shared console must sanitize everything printed through it"
    )

    stream = StringIO()
    safe_console = SanitizingConsole(
        file=stream, width=200, force_terminal=False, color_system=None
    )
    safe_console.print(
        "vis\x1b[31mible\x1b[0m \x00\x07\x9b\x1b]0;pwned\x07 bell\tkept"
    )
    output = stream.getvalue()

    assert "visible" in output
    assert "bell" in output
    assert "\x1b" not in output, "an escape sequence reached the terminal"
    assert "\x00" not in output and "\x07" not in output
    assert "\x9b" not in output, "a C1 control reached the terminal"
    assert "31m" not in output, "the CSI parameters survived the escape"
    assert "pwned" not in output, "an OSC title sequence reached the terminal"

    # Newline and tab stay printable; every other C0/C1 control goes.
    kept = sanitize_console_text("a\tb\nc\x00d\x1be\x9bf")
    assert kept == "a\tb\ncdef"

    # Rich tables are a separate write path: their cells are not strings passed
    # to print(), so the console must sanitize those too.
    from rich.table import Table

    table = Table(title="evil\x1b]0;pwned\x07", show_footer=True)
    table.add_column("Name\x1b[31m", footer="foot\x07")
    table.add_row("evil\x1b[31mname\x07")
    table_stream = StringIO()
    table_console = SanitizingConsole(
        file=table_stream, width=120, force_terminal=False, color_system=None
    )
    table_console.print(table)
    table_output = table_stream.getvalue()
    assert "evil" in table_output
    assert "\x1b" not in table_output, "a table cell carried an escape sequence"
    assert "31m" not in table_output, "a table cell leaked CSI parameters"
    assert "pwned" not in table_output, "a table title carried an OSC sequence"
    assert "Name" in table_output, "the header text itself must survive"
    assert "foot" in table_output, "the footer text itself must survive"


def test_digest_strips_controls() -> None:
    """The digest text carries no control characters or escape sequences."""
    from cartog.core.model import Graph, Node
    from cartog.render.views import generate_digest

    graph = Graph()
    graph.meta = {"target_path": "/tmp/evil\x1b[31mname\x07"}
    graph.add_node(
        Node(
            id="file_evil",
            name="evil\x1b[2J\x07.py",
            qualified_name="evil\x1b[2J\x07.py",
            kind="file",
            path="src/evil\x1b[31m.py",
        )
    )

    digest = generate_digest(graph)

    assert "evil" in digest
    assert "\x1b" not in digest, "an escape sequence reached the digest"
    assert "\x07" not in digest and "\x00" not in digest
    assert not any(
        (ord(char) < 32 and char not in "\n\t") or 0x7F <= ord(char) <= 0x9F
        for char in digest
    )


def test_rich_dependency_is_pinned() -> None:
    """Rich is a direct, upper-bounded dependency because the sanitiser is version-sensitive.

    ``SanitizingConsole`` rewrites ``Column._cells``; Rich exposes no public way
    to replace the cells of a built table, so a major upgrade could move or
    rename that attribute and the control would depend on an unpinned transitive
    dependency of Typer.
    """
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    specs = [dep for dep in data["project"]["dependencies"] if dep.startswith("rich")]
    assert specs, (
        "rich must be a direct dependency: cartog/cli/shared.py mutates Column._cells"
    )

    spec = specs[0]
    upper = re.search(r"<\s*(\d+)", spec)
    assert upper, f"rich needs an upper bound, not {spec!r}: a major bump can rename Column._cells"

    installed = parse_version(dist_version("rich"))
    assert installed[0] < int(upper.group(1)), (
        f"installed rich {dist_version('rich')} is outside the pinned range {spec!r}"
    )


# --------------------------------------------------------------------------- S7


def test_vendor_asset_hashes_match_lock() -> None:
    """Every vendored library is pinned by version, licence and SHA-256."""
    import hashlib

    assets = PACKAGE_ROOT / "render" / "assets"
    lock_path = assets / "VENDOR_LOCK.json"
    assert lock_path.is_file(), "vendored assets need VENDOR_LOCK.json"

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    entries = {entry["file"]: entry for entry in lock["assets"]}

    vendored = {path.name for path in assets.glob("*.js")} - {"viewer.js"}
    assert set(entries) == vendored, "the lock and the vendored files disagree"

    for filename, entry in entries.items():
        assert entry["name"], f"{filename} has no upstream name"
        assert re.fullmatch(r"\d+\.\d+\.\d+", entry["version"]), (
            f"{filename} has no pinned version"
        )
        assert entry["license"], f"{filename} has no licence"
        digest = hashlib.sha256(
            (assets / filename).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        assert entry["sha256"] == digest, (
            f"{filename} does not match its pinned SHA-256 (content changed?)"
        )


def test_doctor_checks_tool_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    """doctor flags an installed tool below the documented minimum."""
    from io import StringIO

    from cartog.cli.commands import doctor as doctor_module
    from cartog.cli.shared import SanitizingConsole
    from cartog.core.toolchain import (
        MINIMUM_TOOL_VERSIONS,
        parse_version,
        version_meets_minimum,
    )

    required = {"node", "mmdc", "scip-python", "scip-typescript", "madge"}
    assert required <= set(MINIMUM_TOOL_VERSIONS), "a checked tool has no minimum"
    assert parse_version("v22.13.0") == (22, 13, 0)
    assert parse_version("12.0.0\n") == (12, 0, 0)
    assert version_meets_minimum("node", "v22.13.0")
    assert not version_meets_minimum("node", "v10.0.0")

    class FakeResult:
        ok = True
        returncode = 0
        stdout = "v0.0.1"
        stderr = ""

    monkeypatch.setattr(
        doctor_module.shutil, "which", lambda name: f"C:/fake/{name}"
    )
    monkeypatch.setattr(doctor_module, "run_process", lambda *a, **k: FakeResult())
    stream = StringIO()
    monkeypatch.setattr(
        doctor_module,
        "console",
        SanitizingConsole(
            file=stream, width=200, force_terminal=False, color_system=None
        ),
    )

    doctor_module.doctor()

    output = stream.getvalue()
    assert "below minimum" in output, "doctor did not report the old versions"
    assert "minimum v" in output, "the report does not state the required version"


# --------------------------------------------------------------------------- S8


def test_limits_are_enforced(tmp_path: Path) -> None:
    """File-count, node-count and edge-count limits stop the run."""
    from cartog.cli.shared import _execute_parse
    from cartog.core.limits import (
        AnalysisLimitError,
        enforce_file_count,
        enforce_graph_size,
    )

    with pytest.raises(AnalysisLimitError, match="file limit"):
        enforce_file_count(5, 4)
    with pytest.raises(AnalysisLimitError, match="graph node limit"):
        enforce_graph_size(11, 0, max_nodes=10, max_edges=10)
    with pytest.raises(AnalysisLimitError, match="edge limit"):
        enforce_graph_size(1, 11, max_nodes=10, max_edges=10)

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "b.py").write_text("y = 2\n", encoding="utf-8")

    with pytest.raises(AnalysisLimitError, match="--max-files"):
        _execute_parse(
            path=str(repo),
            out=str(tmp_path / "out"),
            no_max_file_size=True,
            max_files=1,
        )


def test_limits_are_reported_in_meta() -> None:
    """meta.json carries every active limit, so a run is self-describing."""
    from cartog.core.output import build_meta

    limits = {
        "max_file_size_mb": 1.0,
        "max_files": 10,
        "max_graph_nodes": 20,
        "max_graph_edges": 30,
    }
    meta = build_meta(
        run_id="20260101T000000Z",
        status="complete",
        project={"name": "p", "hash": "h", "path": "/p"},
        target={"path": "/p", "languages": ["python"]},
        options={},
        counts={"files": 1, "nodes": 2, "edges": 3},
        tools={"cartog": "0.0.0", "scip_python": None, "mmdc": None},
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        cartog_version="0.0.0",
        limits=limits,
    )
    assert meta["limits"] == limits


# --------------------------------------------------------------------------- S9


def test_security_doc_links_resolve() -> None:
    """SECURITY.md exists, is linked from the entry docs, and links resolve."""
    security = REPO_ROOT / "SECURITY.md"
    assert security.is_file(), "the threat model must live at SECURITY.md"

    for entry in ("README.md", "docs/HANDOFF.md"):
        text = (REPO_ROOT / entry).read_text(encoding="utf-8")
        assert "SECURITY.md" in text, f"{entry} does not link to SECURITY.md"

    body = security.read_text(encoding="utf-8")
    for required in (
        "untrusted",
        "subprocess",
        "escaping",
        "path confinement",
        "redaction",
        "not protected",
    ):
        assert required.lower() in body.lower(), (
            f"SECURITY.md does not cover {required!r}"
        )

    for target in re.findall(r"\]\(([^)\s]+)\)", body):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#", 1)[0]
        assert (REPO_ROOT / path_part).exists(), (
            f"SECURITY.md links to a missing path: {target}"
        )
