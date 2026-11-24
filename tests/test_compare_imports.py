"""V4: `scripts/compare_imports.py` checked against grimp on a fixture.

The fixture has a package with relative imports, a subpackage, and a package
``__init__`` re-export. Cartog and grimp must produce the same file-to-file
pairs; the report must then say precision and recall are 1.0 with nothing
excluded.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "compare_imports.py"


def _load():
    """Load ``scripts/compare_imports.py`` as a module (``scripts`` is not a package)."""
    spec = importlib.util.spec_from_file_location("cartog_compare_imports", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    pkg = repo / "pkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "__init__.py").write_text("from .core import thing\n", encoding="utf-8")
    (pkg / "core.py").write_text("thing = 1\n", encoding="utf-8")
    (pkg / "a.py").write_text(
        "from . import core\nfrom .sub.mod import other\n", encoding="utf-8"
    )
    (pkg / "sub" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "sub" / "mod.py").write_text("from ..core import thing\n", encoding="utf-8")
    return repo


def test_compare_imports_matches_fixture_edges(tmp_path):
    """Cartog's import pairs equal grimp's on the fixture, and the report says so."""
    module = _load()
    repo = _fixture(tmp_path)

    ours = module.cartog_edges(repo)
    theirs = module.grimp_edges(repo)

    assert ours == theirs, {
        "only_cartog": sorted(ours - theirs),
        "only_grimp": sorted(theirs - ours),
    }
    assert len(ours) >= 4

    data = module.report(repo, "grimp")
    assert data["excluded"] == 0
    assert data["precision"] == 1.0
    assert data["recall"] == 1.0
    assert data["only_ours"] == []
    assert data["only_theirs"] == []
    json.dumps(data)


def test_compare_imports_reports_precision_recall():
    """The scoring is set arithmetic, and an empty side reports no ratio."""
    module = _load()
    ours = {("a", "b"), ("b", "c"), ("a", "c")}
    theirs = {("a", "b"), ("b", "c"), ("c", "d")}

    data = module.compare_edges(ours, theirs)
    assert data["ours"] == 3
    assert data["theirs"] == 3
    assert data["true_positives"] == 2
    assert data["precision"] == pytest.approx(2 / 3)
    assert data["recall"] == pytest.approx(2 / 3)
    assert data["only_ours"] == [("a", "c")]
    assert data["only_theirs"] == [("c", "d")]

    empty = module.compare_edges(set(), set())
    assert empty["precision"] is None
    assert empty["recall"] is None
    assert module.compare_edges(ours, set())["recall"] is None
    assert module.compare_edges(set(), theirs)["precision"] is None
