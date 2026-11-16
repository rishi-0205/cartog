"""R4: the package-layout document must cover every file under ``cartog/``.

R5-R11 move modules along the plan in ``docs/dev/PACKAGE_LAYOUT.md``. If a file
appears that the plan does not mention, the plan is stale and the move will
guess; this test fails instead.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYOUT = REPO_ROOT / "docs" / "dev" / "PACKAGE_LAYOUT.md"
PACKAGE = REPO_ROOT / "cartog"

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
    assert "test_public_imports_after_move" in text, (
        "the compatibility-shim rule must name the test that enforces it"
    )


# Every completed move: the old flat path must stay importable and expose the
# same objects as the new home. Extended by each migration task (R5-R11).
COMPLETED_MOVES: dict[str, str] = {
    "cartog.model": "cartog.core.model",
    "cartog.config": "cartog.core.config",
    "cartog.jsonc": "cartog.core.jsonc",
    "cartog.scan": "cartog.scan.walk",
    "cartog.cache": "cartog.scan.cache",
    "cartog.manifests": "cartog.scan.manifests",
}


def test_public_imports_after_move() -> None:
    import importlib
    import types

    def public_api(module: types.ModuleType, module_name: str) -> list[str]:
        """The module's declared API, falling back to what it appears to own."""
        declared = getattr(module, "__all__", None)
        if declared is not None:
            assert all(isinstance(n, str) for n in declared), f"{module_name}.__all__ is malformed"
            return list(declared)

        names: list[str] = []
        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = getattr(module, name)
            if isinstance(obj, types.ModuleType):
                continue
            if name.isupper() or getattr(obj, "__module__", None) == module_name:
                names.append(name)
        return names

    for old_name, new_name in COMPLETED_MOVES.items():
        old = importlib.import_module(old_name)
        new = importlib.import_module(new_name)

        public = public_api(new, new_name)
        assert public, f"{new_name} exports nothing public"

        missing = [n for n in public if not hasattr(old, n)]
        assert not missing, f"{old_name} no longer re-exports {missing} from {new_name}"

        differing = [
            n for n in public if getattr(old, n, None) is not getattr(new, n, None)
        ]
        assert not differing, (
            f"{old_name} and {new_name} disagree on {differing}; the old path must be "
            "a re-export shim, not a copy"
        )
