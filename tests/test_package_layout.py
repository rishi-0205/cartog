"""Package-layout guard: the document covers every file, and the shims are gone.

R4-R11 moved modules along the plan in ``docs/dev/PACKAGE_LAYOUT.md``. C1 then
deleted the flat compatibility shims. The tests fail if the document is stale,
if a removed path reappears, or if a new home stops importing.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYOUT = REPO_ROOT / "docs" / "dev" / "PACKAGE_LAYOUT.md"
PACKAGE = REPO_ROOT / "cartog"

# C1 deletes the flat compatibility shims and the cartog.langs package.
REMOVED_PATHS = (
    "cartog/cache.py",
    "cartog/config.py",
    "cartog/export_html.py",
    "cartog/export_json.py",
    "cartog/export_mermaid.py",
    "cartog/jsonc.py",
    "cartog/manifests.py",
    "cartog/merge.py",
    "cartog/model.py",
    "cartog/scip_pass.py",
    "cartog/scip_pb2.py",
    "cartog/validate.py",
    "cartog/views.py",
    "cartog/langs",
)

REMOVED_MODULES = (
    "cartog.cache",
    "cartog.config",
    "cartog.export_html",
    "cartog.export_json",
    "cartog.export_mermaid",
    "cartog.jsonc",
    "cartog.manifests",
    "cartog.merge",
    "cartog.model",
    "cartog.scip_pass",
    "cartog.scip_pb2",
    "cartog.validate",
    "cartog.views",
    "cartog.langs",
    "cartog.langs.base",
    "cartog.langs.python_adapter",
    "cartog.langs.js_adapter",
)

NEW_HOMES = (
    "cartog.core",
    "cartog.core.model",
    "cartog.core.config",
    "cartog.core.jsonc",
    "cartog.core.diagnostics",
    "cartog.scan",
    "cartog.scan.walk",
    "cartog.scan.cache",
    "cartog.scan.manifests",
    "cartog.parse",
    "cartog.parse.base",
    "cartog.parse.python_adapter",
    "cartog.parse.js_adapter",
    "cartog.scip",
    "cartog.scip.runner",
    "cartog.scip.scip_pb2",
    "cartog.graph",
    "cartog.graph.merge",
    "cartog.graph.validate",
    "cartog.render",
    "cartog.render.views",
    "cartog.render.export_json",
    "cartog.render.export_mermaid",
    "cartog.render.export_html",
    "cartog.cli",
    "cartog.cli.shared",
)

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*(R\d+|—)\s*\|$", re.MULTILINE)


def _rows() -> list[tuple[str, str, str]]:
    text = LAYOUT.read_text(encoding="utf-8")
    return [(m.group(1), m.group(2), m.group(3)) for m in ROW_RE.finditer(text)]


def _package_files() -> list[str]:
    files: list[str] = []
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        files.append(rel)
    return files


def _covered(rel: str, mapped: set[str]) -> bool:
    if rel in mapped:
        return True
    for entry in mapped:
        if entry.endswith("/*") and rel.startswith(entry[:-1]):
            return True
    return False


def test_layout_doc_covers_every_module() -> None:
    rows = _rows()
    assert rows, f"no mapping table found in {LAYOUT}"

    current = {src for src, _, _ in rows if src != "(new)"}
    targets = {dst for _, dst, _ in rows}

    missing_source = [p for p in _package_files() if not _covered(p, current | targets)]
    assert not missing_source, (
        "these files under cartog/ have no destination in docs/dev/PACKAGE_LAYOUT.md:\n"
        + "\n".join(missing_source)
    )

    def _exists(entry: str) -> bool:
        if entry.endswith("/*"):
            return any(
                p.startswith(entry[:-1]) for p in _package_files()
            )
        return (REPO_ROOT / entry).exists()

    # The table is the R4 plan. After a move, the "current path" cell is the
    # historical path and the "new path" cell is the real one; a row is spelled
    # correctly when at least one of the two exists.
    def _row_exists(src: str, dst: str) -> bool:
        return _exists(src) or _exists(dst)

    by_source = {src: dst for src, dst, _ in rows if src != "(new)"}
    stale = sorted(
        src for src, dst in by_source.items() if not _row_exists(src, dst)
    )
    assert not stale, (
        "docs/dev/PACKAGE_LAYOUT.md lists paths that exist on neither side "
        "(fix the table):\n" + "\n".join(stale)
    )

    tasks = {task for _, _, task in rows}
    for expected in ("R5", "R6", "R7", "R8", "R9", "R10", "R11"):
        assert expected in tasks, f"the mapping table has no row owned by {expected}"

    text = LAYOUT.read_text(encoding="utf-8")
    for heading in ("Import rules", "Package-data risks", "Migration order"):
        assert heading in text, f"the layout document is missing the {heading!r} section"
    assert "cartog.cli:app" in text, "the console entry point must be called out"
    assert "test_shims_are_gone" in text, (
        "the removal rule must name the test that enforces it"
    )
    assert "test_public_imports_after_move" not in text, (
        "the document must not name the compatibility test that C1 deletes"
    )

    removed_section = text.split("## 6. Removed by C1", 1)
    assert len(removed_section) == 2, "the layout document needs a '## 6. Removed by C1' list"
    for rel in REMOVED_PATHS:
        assert f"`{rel}`" in removed_section[1], (
            f"the 'Removed by C1' list does not name {rel}"
        )


def test_cli_package_layout() -> None:
    """R11: the CLI is a package with shared helpers and one module per command."""
    import importlib

    import typer.main

    shared = importlib.import_module("cartog.cli.shared")
    cli = importlib.import_module("cartog.cli")

    assert isinstance(shared.app, typer.Typer), "cartog.cli.shared must own the Typer app"
    assert cli.app is shared.app, "cartog.cli must re-export the same app object"
    assert callable(shared._resolve_graph), "helpers live in cartog.cli.shared"

    for name in (
        "doctor",
        "parse",
        "scip",
        "build",
        "map",
        "check",
        "flow",
        "digest",
        "view",
        "queries",
    ):
        assert importlib.import_module(f"cartog.cli.commands.{name}"), f"missing command module {name}"

    command = typer.main.get_command(cli.app)
    assert sorted(command.commands) == [
        "build",
        "check",
        "digest",
        "doctor",
        "flow",
        "map",
        "parse",
        "query",
        "scip",
        "view",
    ], f"CLI surface changed: {sorted(command.commands)}"
    assert sorted(command.commands["query"].commands) == ["callees-of", "callers-of"]


def test_shims_are_gone() -> None:
    """C1: every compatibility shim and cartog.langs is deleted for good."""
    import importlib
    import importlib.util

    import typer

    import cartog.cli
    import cartog.scan

    def spec_exists(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except ModuleNotFoundError:
            return False

    for rel in REMOVED_PATHS:
        assert not (REPO_ROOT / rel).exists(), f"{rel} still exists; C1 deletes it"
    for name in REMOVED_MODULES:
        assert not spec_exists(name), f"{name} is still importable; C1 deletes it"

    for name in NEW_HOMES:
        assert importlib.import_module(name), f"new home {name} does not import"

    assert callable(cartog.scan.walk_files), "cartog.scan must keep re-exporting walk_files"
    assert isinstance(cartog.cli.app, typer.Typer), "cartog.cli.app must stay the Typer app"
