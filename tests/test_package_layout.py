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

    stale = sorted(src for src in current if not _exists(src))
    assert not stale, (
        "docs/dev/PACKAGE_LAYOUT.md lists paths that do not exist (update the table):\n"
        + "\n".join(stale)
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
