"""Tests for Milestone 9: Deterministic Noise Filtering for Views.

Validates heuristic detection of re-export barrel files, constants/type-only modules,
import edge rewiring through noise modules, and --show-noise CLI toggle.
"""

from pathlib import Path

from typer.testing import CliRunner

from cartog.cli import app
from cartog.model import Edge, Graph, Node
from cartog.views import (
    NoiseCategory,
    detect_noise_files,
    rewire_view_edges,
)

runner = CliRunner()


def test_detect_python_reexport_barrel(tmp_path: Path):
    """Verify that a Python barrel file with re-exports and PEP 562 deprecation shim is classified as noise."""
    repo = tmp_path / "repo"
    repo.mkdir()
    pkg = repo / "pkg"
    pkg.mkdir()

    # Re-export barrel with PEP 562 __getattr__ shim (Click pattern)
    init_content = """\"\"\"Package barrel.\"\"\"
from __future__ import annotations
from .core import Command as Command
from .utils import echo as echo

__all__ = ["Command", "echo"]

def __getattr__(name: str):
    if name == "OldCommand":
        from .core import Command
        return Command
    raise AttributeError(name)
"""
    (pkg / "__init__.py").write_text(init_content, encoding="utf-8")
    (pkg / "core.py").write_text("class Command: pass\n", encoding="utf-8")
    (pkg / "utils.py").write_text("def echo(msg: str): print(msg)\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    res = runner.invoke(app, ["map", str(repo), "--out", str(out_dir), "--no-scip"])
    assert res.exit_code == 0

    graph = Graph.load(out_dir / "graph.json")
    noise = detect_noise_files(graph, target_path=repo)

    assert "pkg/__init__.py" in noise
    assert noise["pkg/__init__.py"].category == NoiseCategory.REEXPORT.value
    assert "pkg/core.py" not in noise
    assert "pkg/utils.py" not in noise


def test_detect_python_constants_and_types(tmp_path: Path):
    """Verify that Python constants-only and TypedDict/Enum type-only modules are detected as noise."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # 1. Constants file
    const_content = """\"\"\"Application constants.\"\"\"
DEBUG = False
MAX_RETRIES = 5
TIMEOUT_SECONDS = 30.0
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CONFIG_MAP = {"env": "production"}
"""
    (repo / "constants.py").write_text(const_content, encoding="utf-8")

    # 2. Types file
    types_content = """\"\"\"Type definitions.\"\"\"
from typing import TypedDict, TypeVar, Optional
from enum import Enum

T = TypeVar("T")

class UserRole(str, Enum):
    ADMIN = "admin"
    GUEST = "guest"

class UserProfile(TypedDict):
    id: int
    name: str
    role: UserRole
"""
    (repo / "types.py").write_text(types_content, encoding="utf-8")

    # 3. Active logic file
    (repo / "app.py").write_text("def run_app(): pass\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    res = runner.invoke(app, ["map", str(repo), "--out", str(out_dir), "--no-scip"])
    assert res.exit_code == 0

    graph = Graph.load(out_dir / "graph.json")
    noise = detect_noise_files(graph, target_path=repo)

    assert "constants.py" in noise
    assert noise["constants.py"].category == NoiseCategory.CONSTANTS_OR_TYPES.value
    assert "types.py" in noise
    assert noise["types.py"].category == NoiseCategory.CONSTANTS_OR_TYPES.value
    assert "app.py" not in noise


def test_negative_logic_modules_not_classified_as_noise(tmp_path: Path):
    """Verify that modules with functions or domain classes with logic methods are NOT classified as noise."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Module named 'types.py' but with actual domain logic functions and classes (Click pattern)
    logic_types_content = """\"\"\"Parameter type engine.\"\"\"
class ParamType:
    def convert(self, value, param, ctx):
        return value

    def fail(self, message):
        raise ValueError(message)

def get_best_type():
    return ParamType()
"""
    (repo / "types.py").write_text(logic_types_content, encoding="utf-8")

    # Module named 'globals.py' but with context manager functions (Click pattern)
    logic_globals_content = """\"\"\"Context stack helpers.\"\"\"
def get_current_context():
    return None

def push_context(ctx):
    pass
"""
    (repo / "globals.py").write_text(logic_globals_content, encoding="utf-8")

    out_dir = tmp_path / "out"
    res = runner.invoke(app, ["map", str(repo), "--out", str(out_dir), "--no-scip"])
    assert res.exit_code == 0

    graph = Graph.load(out_dir / "graph.json")
    noise = detect_noise_files(graph, target_path=repo)

    # Neither should be classified as noise because they contain domain functions and class methods
    assert "types.py" not in noise
    assert "globals.py" not in noise


def test_ts_reexport_and_types_detection(tmp_path: Path):
    """Verify TypeScript barrel and type definition files are detected."""
    repo = tmp_path / "ts_repo"
    repo.mkdir()

    # 1. TS barrel index.ts
    (repo / "index.ts").write_text(
        "export * from './core';\nexport { helper } from './utils';\n",
        encoding="utf-8",
    )

    # 2. TS type-only module types.ts
    (repo / "types.ts").write_text(
        "export type ID = string | number;\nexport interface Config { timeout: number; }\n",
        encoding="utf-8",
    )

    # 3. TS core module
    (repo / "core.ts").write_text(
        "export class Engine { start() { return true; } }\n",
        encoding="utf-8",
    )
    (repo / "utils.ts").write_text(
        "export function helper() { return 42; }\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    res = runner.invoke(app, ["map", str(repo), "--out", str(out_dir), "--no-scip"])
    assert res.exit_code == 0

    graph = Graph.load(out_dir / "graph.json")
    noise = detect_noise_files(graph, target_path=repo)

    assert "index.ts" in noise
    assert noise["index.ts"].category == NoiseCategory.REEXPORT.value
    assert "types.ts" in noise
    assert noise["types.ts"].category == NoiseCategory.CONSTANTS_OR_TYPES.value
    assert "core.ts" not in noise
    assert "utils.ts" not in noise


def test_import_rewiring_through_reexport_barrel():
    """Verify rewire_view_edges bridges A -> B -> C into A -> C when B is a noise barrel."""
    # Construct synthetic graph:
    # fa (test.py) -> fb (__init__.py) -> fc (utils.py)
    fa = Node.create(kind="file", name="test.py", qualified_name="tests/test.py", path="tests/test.py")
    fb = Node.create(kind="file", name="__init__.py", qualified_name="src/__init__.py", path="src/__init__.py")
    fc = Node.create(kind="file", name="utils.py", qualified_name="src/utils.py", path="src/utils.py")

    # Functions
    fn_a = Node.create(kind="function", name="test_fn", qualified_name="tests.test.test_fn", path="tests/test.py")
    fn_c = Node.create(kind="function", name="target_fn", qualified_name="src.utils.target_fn", path="src/utils.py")

    e_import_ab = Edge(source=fa.id, target=fb.id, kind="imports", confidence="import", count=1)
    e_import_bc = Edge(source=fb.id, target=fc.id, kind="imports", confidence="import", count=1)
    # Direct SCIP call from test_fn to target_fn
    e_call_ac = Edge(source=fn_a.id, target=fn_c.id, kind="calls", confidence="resolved", count=2)

    graph = Graph(
        schema_version="1.1.0",
        nodes={n.id: n for n in (fa, fb, fc, fn_a, fn_c)},
        edges=[e_import_ab, e_import_bc, e_call_ac],
        meta={"tool_version": "0.1.0"},
    )

    noise_paths = {"src/__init__.py"}
    rewired = rewire_view_edges(graph, noise_paths)

    # 1. Call edge ac should be preserved unmodified
    calls = [e for e in rewired if e.kind == "calls"]
    assert len(calls) == 1
    assert calls[0].source == fn_a.id
    assert calls[0].target == fn_c.id

    # 2. Import edge should be rewired directly from fa to fc
    imports = [e for e in rewired if e.kind == "imports"]
    assert len(imports) == 1
    assert imports[0].source == fa.id
    assert imports[0].target == fc.id
    assert "rewired via" in imports[0].evidence[0]


def test_cli_show_noise_toggle(tmp_path: Path):
    """Verify that --show-noise controls whether noise files appear in overview.mmd and graph.json preserves nodes."""
    repo = tmp_path / "repo"
    repo.mkdir()
    pkg = repo / "pkg"
    pkg.mkdir()

    (pkg / "__init__.py").write_text("from .core import run\n__all__ = ['run']\n", encoding="utf-8")
    (pkg / "core.py").write_text("def run(): pass\n", encoding="utf-8")
    (pkg / "constants.py").write_text("MAX_SIZE = 100\n", encoding="utf-8")
    (repo / "main.py").write_text("from pkg import run\nrun()\n", encoding="utf-8")

    # 1. Default run: noise files filtered from overview.mmd
    out_default = tmp_path / "out_default"
    res1 = runner.invoke(app, ["map", str(repo), "--out", str(out_default), "--no-scip"])
    assert res1.exit_code == 0
    assert "Filtered" in res1.stdout

    mmd_default = (out_default / "overview.mmd").read_text(encoding="utf-8")
    # Neither __init__.py nor constants.py should be rendered in default view
    assert "__init__.py" not in mmd_default
    assert "constants.py" not in mmd_default
    assert "core.py" in mmd_default

    # But graph.json preserves 100% of nodes!
    graph_default = Graph.load(out_default / "graph.json")
    file_paths = {n.path for n in graph_default.nodes.values() if n.kind == "file"}
    assert "pkg/__init__.py" in file_paths
    assert "pkg/constants.py" in file_paths
    assert "pkg/core.py" in file_paths

    # Metadata records filtered paths
    assert "view_noise_filtered" in graph_default.meta
    assert "pkg/__init__.py" in graph_default.meta["view_noise_filtered"]
    assert "pkg/constants.py" in graph_default.meta["view_noise_filtered"]

    # 2. Run with --show-noise: all files rendered
    out_shown = tmp_path / "out_shown"
    res2 = runner.invoke(app, ["map", str(repo), "--out", str(out_shown), "--no-scip", "--show-noise"])
    assert res2.exit_code == 0

    mmd_shown = (out_shown / "overview.mmd").read_text(encoding="utf-8")
    assert "__init__.py" in mmd_shown
    assert "constants.py" in mmd_shown
    assert "core.py" in mmd_shown


def test_noise_filtering_typing_module(tmp_path: Path):
    """Verify that a typing.py module with type checking guards and type aliases is classified as noise and hidden by default."""
    repo = tmp_path / "repo"
    repo.mkdir()

    typing_code = """\"\"\"Typing definitions.\"\"\"
from __future__ import annotations
import typing as t

if t.TYPE_CHECKING:
    from .core import CoreClass

Callback = t.Callable[[str], None]
Options = t.Dict[str, t.Any]
T = t.TypeVar("T")
"""
    (repo / "typing.py").write_text(typing_code, encoding="utf-8")
    (repo / "core.py").write_text("class CoreClass: pass\n", encoding="utf-8")
    (repo / "main.py").write_text("from .core import CoreClass\ndef main(): pass\n", encoding="utf-8")

    # 1. Default map run: typing.py must be detected as noise and hidden from overview.mmd
    out_default = tmp_path / "out_default"
    res1 = runner.invoke(app, ["map", str(repo), "--out", str(out_default), "--no-scip"])
    assert res1.exit_code == 0

    graph_default = Graph.load(out_default / "graph.json")
    assert "view_noise_filtered" in graph_default.meta
    assert "typing.py" in graph_default.meta["view_noise_filtered"]
    assert graph_default.meta["view_noise_filtered"]["typing.py"]["category"] == NoiseCategory.CONSTANTS_OR_TYPES.value

    mmd_default = (out_default / "overview.mmd").read_text(encoding="utf-8")
    assert "typing.py" not in mmd_default
    assert "core.py" in mmd_default

    # 2. --show-noise map run: typing.py must be rendered in overview.mmd
    out_shown = tmp_path / "out_shown"
    res2 = runner.invoke(app, ["map", str(repo), "--out", str(out_shown), "--no-scip", "--show-noise"])
    assert res2.exit_code == 0
    mmd_shown = (out_shown / "overview.mmd").read_text(encoding="utf-8")
    assert "typing.py" in mmd_shown


def test_noise_filtering_meta_preservation(tmp_path: Path):
    """Verify that noise filtering preserves all nodes and edges in graph.json and records rich classification metadata."""
    repo = tmp_path / "repo"
    repo.mkdir()

    typing_code = """import typing as t
if t.TYPE_CHECKING:
    import sys
UserType = str
"""
    (repo / "typing.py").write_text(typing_code, encoding="utf-8")
    (repo / "constants.py").write_text("API_VERSION = 1\n", encoding="utf-8")
    (repo / "service.py").write_text("def serve(): pass\n", encoding="utf-8")

    out_dir = tmp_path / "out_meta"
    res = runner.invoke(app, ["map", str(repo), "--out", str(out_dir), "--no-scip"])
    assert res.exit_code == 0

    graph = Graph.load(out_dir / "graph.json")

    # All 3 files must remain in graph.nodes
    file_paths = {n.path for n in graph.nodes.values() if n.kind == "file"}
    assert "typing.py" in file_paths
    assert "constants.py" in file_paths
    assert "service.py" in file_paths

    # Metadata must record path, category, and reason for both filtered files
    filtered_meta = graph.meta.get("view_noise_filtered", {})
    assert "typing.py" in filtered_meta
    assert "constants.py" in filtered_meta
    assert filtered_meta["typing.py"]["category"] == NoiseCategory.CONSTANTS_OR_TYPES.value
    assert len(filtered_meta["typing.py"]["reason"]) > 0
    assert filtered_meta["constants.py"]["category"] == NoiseCategory.CONSTANTS_OR_TYPES.value
    assert len(filtered_meta["constants.py"]["reason"]) > 0


