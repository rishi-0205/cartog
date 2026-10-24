"""Unit tests for SCIP decoding, range translation, occurrence extraction, and call linking."""

from pathlib import Path
import pytest

from cartog.langs import parse_source_file
from cartog.langs.base import SymbolRecord
from cartog.model import SourceRange
from cartog.scan import walk_files
from cartog.scip_pass import (
    ScipIndexResult,
    decode_scip_index,
    find_enclosing_symbol,
    link_calls,
    normalize_scip_range,
    run_scip_indexer,
)


def test_normalize_scip_range():
    """Verify SCIP 3-tuple and 4-tuple ranges convert correctly to SourceRange."""
    # 3-tuple [line, startCol, endCol] (SCIP 0-based line 10 becomes 1-based line 11)
    r1 = normalize_scip_range([10, 5, 15])
    assert r1.start_line == 11
    assert r1.start_col == 5
    assert r1.end_line == 11
    assert r1.end_col == 15

    # 4-tuple [startLine, startCol, endLine, endCol] (SCIP 0-based lines 12..18 become 13..19)
    r2 = normalize_scip_range([12, 4, 18, 20])
    assert r2.start_line == 13
    assert r2.start_col == 4
    assert r2.end_line == 19
    assert r2.end_col == 20

    # Fallback
    r3 = normalize_scip_range([5])
    assert r3.start_line == 1


def test_decode_prebuilt_scip_fixture():
    """Verify decoding prebuilt binary index.scip fixture."""
    fixture_path = Path("tests/fixtures/prebuilt_scip/index.scip")
    if not fixture_path.is_file():
        pytest.skip("prebuilt index.scip fixture not found")

    res = decode_scip_index(fixture_path)
    assert res.ran is True
    assert res.error is None
    assert len(res.documents) == 4

    doc_paths = [d.relative_path for d in res.documents]
    assert any("utils.ts" in p for p in doc_paths)
    assert any("app.ts" in p for p in doc_paths)

    total_defs = sum(len(d.definitions) for d in res.documents)
    total_refs = sum(len(d.references) for d in res.documents)
    assert total_defs > 0
    assert total_refs > 0

    # Verify formatGreeting symbol definition is extracted
    greeting_defs = [
        sym for sym in res.definitions_by_symbol.keys() if sym.endswith("formatGreeting().")
    ]
    assert len(greeting_defs) == 1


def test_find_enclosing_symbol():
    """Verify finding the innermost function or method enclosing a target range."""
    symbols = [
        SymbolRecord(
            kind="class",
            name="MyClass",
            qualified_name="pkg.MyClass",
            start_line=1,
            start_col=0,
            end_line=20,
            end_col=1,
        ),
        SymbolRecord(
            kind="method",
            name="my_method",
            qualified_name="pkg.MyClass.my_method",
            start_line=5,
            start_col=4,
            end_line=15,
            end_col=5,
            parent="MyClass",
        ),
        SymbolRecord(
            kind="function",
            name="standalone",
            qualified_name="pkg.standalone",
            start_line=25,
            start_col=0,
            end_line=30,
            end_col=1,
        ),
    ]

    # Target range inside my_method
    target_inside_method = SourceRange(start_line=8, start_col=8, end_line=8, end_col=15)
    matched = find_enclosing_symbol(target_inside_method, symbols)
    assert matched is not None
    assert matched.name == "my_method"
    assert matched.kind == "method"

    # Target range in class body but outside method
    target_in_class = SourceRange(start_line=2, start_col=4, end_line=2, end_col=10)
    matched_class = find_enclosing_symbol(target_in_class, symbols)
    assert matched_class is not None
    assert matched_class.name == "MyClass"

    # Target range completely outside
    target_outside = SourceRange(start_line=100, start_col=0, end_line=100, end_col=5)
    assert find_enclosing_symbol(target_outside, symbols) is None


def test_link_calls_from_prebuilt_fixture():
    """Verify correlating caller function to callee function to create CallEdgeCandidate."""
    fixture_path = Path("tests/fixtures/prebuilt_scip/index.scip")
    if not fixture_path.is_file():
        pytest.skip("prebuilt index.scip fixture not found")

    scip_res = decode_scip_index(fixture_path)
    assert scip_res.ran is True

    # Parse source files in ts_monorepo to extract Tree-sitter symbol hierarchy
    scan_res = walk_files("tests/fixtures/ts_monorepo")
    parsed_files = [parse_source_file(f) for f in scan_res.files]
    symbols_by_file = {f.path: f.symbols for f in parsed_files}

    candidates = link_calls(scip_res, symbols_by_file)
    assert len(candidates) > 0

    # Verify runWebApp calls formatGreeting
    call_pairs = [
        (c.caller_symbol, c.callee_symbol) for c in candidates
    ]
    assert ("runWebApp", "formatGreeting") in call_pairs

    matched_cand = [
        c for c in candidates if c.caller_symbol == "runWebApp" and c.callee_symbol == "formatGreeting"
    ][0]
    assert len(matched_cand.evidence) > 0
    assert "app.ts:6" in matched_cand.evidence[0]


def test_decode_scip_nonexistent_file():
    """Verify decode_scip_index fails gracefully on missing files."""
    res = decode_scip_index("nonexistent/path/index.scip")
    assert res.ran is False
    assert "not found" in res.error.lower()


def test_run_scip_indexer_fallback_on_unsupported_environment(tmp_path):
    """Verify run_scip_indexer returns ran=False and reason on failure without crashing."""
    res = run_scip_indexer("nonexistent", tmp_path / "out", language="unknown_language")
    assert res.ran is False
    assert res.error is not None


def test_scip_typescript_live_indexer_execution(tmp_path):
    """Verify live scip-typescript indexer execution on ts_monorepo fixture."""
    res = run_scip_indexer("tests/fixtures/ts_monorepo", tmp_path, language="typescript")
    assert res.ran is True
    assert res.error is None
    assert len(res.documents) == 4

    doc_paths = [d.relative_path for d in res.documents]
    assert any("utils.ts" in p for p in doc_paths)
    assert any("app.ts" in p for p in doc_paths)

    greeting_defs = [
        sym for sym in res.definitions_by_symbol.keys() if sym.endswith("formatGreeting().")
    ]
    assert len(greeting_defs) == 1


def test_scip_typescript_missing_node_modules_hint(tmp_path):
    """Verify hint is included in error when scip-typescript fails on missing node_modules."""
    dummy_repo = tmp_path / "dummy_repo"
    dummy_repo.mkdir()
    (dummy_repo / "package.json").write_text('{"name": "dummy"}', encoding="utf-8")
    (dummy_repo / "tsconfig.json").write_text('{"extends": "@nonexistent/tsconfig"}', encoding="utf-8")

    res = run_scip_indexer(dummy_repo, tmp_path / "out", language="typescript")
    assert res.ran is False
    assert res.error is not None
    assert "node_modules" in res.error.lower()


def test_scip_indexer_untruncated_error_and_log(tmp_path):
    """Verify SCIP indexer failure saves untruncated error and writes scip_error.log."""
    out_dir = tmp_path / "out"
    res = run_scip_indexer("nonexistent", out_dir, language="unknown_lang")
    assert res.ran is False
    assert res.error is not None
    # Verify error is not sliced to 100 characters
    log_file = out_dir / "scip_error.log"
    assert log_file.is_file()
    assert log_file.read_text(encoding="utf-8") == res.error


def test_known_call_evidence_line_against_source():
    """Verify that decoded SCIP call evidence produces an exact 1-based line matching source code."""
    fixture_path = Path("tests/fixtures/prebuilt_scip/index.scip")
    if not fixture_path.is_file():
        pytest.skip("prebuilt index.scip fixture not found")

    scip_res = decode_scip_index(fixture_path)
    assert scip_res.ran is True

    scan_res = walk_files("tests/fixtures/ts_monorepo")
    parsed_files = [parse_source_file(f) for f in scan_res.files]
    symbols_by_file = {f.path: f.symbols for f in parsed_files}

    candidates = link_calls(scip_res, symbols_by_file)
    cand = next(
        c for c in candidates if c.caller_symbol == "runWebApp" and c.callee_symbol == "formatGreeting"
    )

    # Cand evidence must be 1-based line 6
    assert any("app.ts:6" in ev for ev in cand.evidence)

    # Verify against actual source file
    source_file = Path("tests/fixtures/ts_monorepo/packages/web/src/app.ts")
    lines = source_file.read_text(encoding="utf-8").splitlines()
    # 1-based line 6 (index 5)
    line_6 = lines[5]
    assert "formatGreeting('Cartog')" in line_6



