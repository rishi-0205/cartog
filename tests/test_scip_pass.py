"""Unit tests for SCIP decoding, range translation, occurrence extraction, and call linking."""

from pathlib import Path

import pytest
from conftest import requires_sample

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


def test_audit_scip_calls_and_relationships():
    """Diagnostic audit: inspect SCIP evidence, node/edge records, and call edge breakdown."""
    import json

    from cartog.scip_pb2 import Index

    requires_sample("click")

    # 1. SCIP symbol evidence for click in tests vs src/click
    click_scip_file = Path("cartog-out/click-map-scip/.cartog/scip/281f030a7dc8/index.scip")
    if click_scip_file.is_file():
        idx = Index()
        with open(click_scip_file, "rb") as f:
            idx.ParseFromString(f.read())
        print("\n--- SCIP Documents & Symbols Evidence ---")
        src_docs = []
        test_docs = []
        for d in idx.documents:
            d_norm = d.relative_path.replace("\\", "/")
            if d_norm.startswith("src/"):
                src_docs.append(d)
            elif d_norm.startswith("tests/"):
                test_docs.append(d)
        print(f"Total documents: {len(idx.documents)} (src: {len(src_docs)}, tests: {len(test_docs)})")
        
        # Sample defs in src/click
        sample_src_defs = []
        for d in src_docs:
            for occ in d.occurrences:
                if occ.symbol_roles & 0x1 and not occ.symbol.startswith("local "):
                    sample_src_defs.append((d.relative_path, occ.symbol))
        print("Sample src/ definitions (first 3):")
        for p, s in sample_src_defs[:3]:
            print(f"  doc: {p} -> symbol: {s}")

        # Sample refs in tests/ referencing click
        sample_test_refs = []
        for d in test_docs:
            for occ in d.occurrences:
                if "click" in occ.symbol and not occ.symbol.startswith("local "):
                    sample_test_refs.append((d.relative_path, occ.symbol))
        print("Sample tests/ references to click (first 5):")
        for p, s in sample_test_refs[:5]:
            print(f"  doc: {p} -> symbol: {s}")

        # Check relationships in index.scip
        rel_list = []
        for d in idx.documents:
            for s in d.symbols:
                for r in s.relationships:
                    rel_list.append((s.symbol, r.symbol, r.is_implementation, r.is_reference, r.is_type_definition, r.is_definition))
        print(f"\nSCIP Relationships in Click: {len(rel_list)} total")
        for item in rel_list[:5]:
            print(f"  rel: {item}")

    # 2. Check Node Records for ca1921bcb6, 38a54a4bad, d50a1e47c9
    graph_path = Path("cartog-out/click-map-scip/graph.json")
    if graph_path.is_file():
        with open(graph_path, encoding="utf-8") as f:
            graph = json.load(f)
        
        target_ids = {"ca1921bcb6", "38a54a4bad", "d50a1e47c9"}
        found_nodes = {n["id"]: n for n in graph["nodes"] if n["id"] in target_ids}
        print("\n--- Target Node Records ---")
        for tid, n in found_nodes.items():
            print(f"Node {tid}:")
            print(f"  id: {n.get('id')}")
            print(f"  name: {n.get('name')}")
            print(f"  qualified_name: {n.get('qualified_name')}")
            print(f"  path: {n.get('path')}")
            print(f"  range: {n.get('range')}")
            print(f"  kind: {n.get('kind')}")

        print("\n--- Edges from ca1921bcb6 ---")
        for e in graph["edges"]:
            if e["source"] == "ca1921bcb6":
                print(f"  edge: {e}")

        # 3. Categorization of 2,242 calls edges
        import tree_sitter
        import tree_sitter_python
        py_lang = tree_sitter.Language(tree_sitter_python.language())
        parser = tree_sitter.Parser(py_lang)
        trees = {}
        source_lines = {}
        for p in Path("samples/click").rglob("*.py"):
            rel = p.relative_to(Path("samples/click")).as_posix()
            src = p.read_bytes()
            trees[rel] = parser.parse(src)
            source_lines[rel] = src.decode("utf-8", errors="replace").splitlines()

        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        print(f"\nTotal calls edges in graph.json: {len(call_edges)}")

        breakdown = {
            "real_call_expression": 0,
            "decorator": 0,
            "except_or_raise": 0,
            "isinstance_issubclass": 0,
            "class_inheritance": 0,
            "type_annotation": 0,
            "other_reference": 0,
        }

        # For each edge, look up the exact occurrence range from scip.json if available
        scip_json_path = Path("cartog-out/click-map-scip/scip.json")
        scip_data = {}
        if scip_json_path.is_file():
            with open(scip_json_path, encoding="utf-8") as f:
                scip_data = json.load(f)

        # Build map of (doc_path, line) -> occurrence ranges
        # scip_data["documents"]
        doc_occs = {}
        for doc in scip_data.get("documents", []):
            dp = doc["relative_path"]
            doc_occs[dp] = doc.get("occurrences", [])

        # Categorize
        for e in call_edges:
            ev = e.get("evidence", [None])[0]
            if not ev:
                breakdown["other_reference"] += 1
                continue
            fp, lno_s = ev.split(":")
            lno = int(lno_s)
            tree = trees.get(fp)
            lines = source_lines.get(fp, [])
            line_txt = lines[lno - 1].strip() if 1 <= lno <= len(lines) else ""

            if not tree:
                breakdown["other_reference"] += 1
                continue

            row = lno - 1
            # Find all nodes covering this line
            # Let's find if there is a call node on this line that calls the callee
            # Or find the node at the specific identifier
            
            # Check for decorator first
            if line_txt.startswith("@") or line_txt.startswith("def ") or line_txt.startswith("class "):
                # Could be decorator
                is_dec = False
                def check_dec(n):
                    if n.type == "decorator":
                        return True
                    for c in n.children:
                        if check_dec(c):
                            return True
                    return False
                # Check root node at row
                # Let's find smallest node covering line
                desc = tree.root_node.descendant_for_point_range((row, 0), (row, len(lines[row]) if row < len(lines) else 0))
                curr = desc
                while curr:
                    if curr.type == "decorator":
                        is_dec = True
                        break
                    curr = curr.parent
                if is_dec or line_txt.startswith("@"):
                    breakdown["decorator"] += 1
                    continue

            # Check except or raise
            if "except " in line_txt or line_txt.startswith("raise "):
                desc = tree.root_node.descendant_for_point_range((row, 0), (row, len(lines[row]) if row < len(lines) else 0))
                curr = desc
                in_ex = False
                while curr:
                    if curr.type in ("except_clause", "raise_statement"):
                        in_ex = True
                        break
                    curr = curr.parent
                if in_ex or "except " in line_txt or line_txt.startswith("raise "):
                    breakdown["except_or_raise"] += 1
                    continue

            if "isinstance(" in line_txt or "issubclass(" in line_txt:
                breakdown["isinstance_issubclass"] += 1
                continue

            if line_txt.startswith("class ") and "(" in line_txt:
                desc = tree.root_node.descendant_for_point_range((row, 0), (row, len(lines[row]) if row < len(lines) else 0))
                curr = desc
                in_cls = False
                while curr:
                    if curr.type == "argument_list" and curr.parent and curr.parent.type == "class_definition":
                        in_cls = True
                        break
                    curr = curr.parent
                if in_cls:
                    breakdown["class_inheritance"] += 1
                    continue

            # Check type annotation: ': Type' or '-> Type'
            if ": " in line_txt or "->" in line_txt:
                # check if occurrence is in type annotation
                # or if the line is purely a type annotation
                desc = tree.root_node.descendant_for_point_range((row, 0), (row, len(lines[row]) if row < len(lines) else 0))
                curr = desc
                in_type = False
                while curr:
                    if curr.type in ("type", "type_alias", "annotation", "type_clause"):
                        in_type = True
                        break
                    curr = curr.parent
                if in_type:
                    breakdown["type_annotation"] += 1
                    continue

            # Check if there is a call expression on this line
            # Find all call nodes overlapping this line
            def find_calls(n, row=row):
                res = []
                if n.start_point.row <= row <= n.end_point.row:
                    if n.type == "call":
                        res.append(n)
                    for c in n.children:
                        res.extend(find_calls(c))
                return res
            call_nodes = find_calls(tree.root_node)
            if call_nodes:
                breakdown["real_call_expression"] += 1
            else:
                breakdown["other_reference"] += 1

        print("\n--- Accurate Breakdown of Calls Edges ---")
        for k, v in breakdown.items():
            pct = (v / len(call_edges)) * 100
            print(f"  {k}: {v} ({pct:.1f}%)")

        assert len(found_nodes) == 3
        assert found_nodes["38a54a4bad"]["qualified_name"] == "click.core.Command.format_options"
        assert found_nodes["d50a1e47c9"]["qualified_name"] == "click.core.Group.format_options"
        assert found_nodes["ca1921bcb6"]["qualified_name"] == "click.core.Command.format_help"
        ca_edges = [e for e in graph["edges"] if e["source"] == "ca1921bcb6" and e["target"] == "38a54a4bad"]
        assert len(ca_edges) == 1
        assert breakdown["real_call_expression"] > 1000


def test_diagnose_python_and_scip_env():
    """Diagnostic test to find all python interpreters, pip show click, and SCIP metadata."""
    import os
    import subprocess
    import sys

    from cartog.scip_pb2 import Index

    print("\n--- Diagnostic: Python Interpreters & Pip Show Click ---")
    print(f"Current sys.executable: {sys.executable}")
    
    # 1. Run where python
    try:
        where_res = subprocess.run(["where.exe", "python"], capture_output=True, text=True, check=True)
        pythons = [p.strip() for p in where_res.stdout.splitlines() if p.strip()]
    except Exception as e:
        pythons = [sys.executable]
        print(f"where.exe failed: {e}")

    print(f"Python paths found by 'where python' ({len(pythons)}):")
    for py in pythons:
        print(f"  {py}")
        try:
            pip_res = subprocess.run([py, "-m", "pip", "show", "click"], capture_output=True, text=True)
            if pip_res.returncode == 0:
                print(f"    pip show click for {py}:")
                for line in pip_res.stdout.splitlines():
                    if line.startswith("Name:") or line.startswith("Version:") or line.startswith("Location:") or line.startswith("Required-by:"):
                        print(f"      {line}")
            else:
                print(f"    click NOT installed in {py}")
        except Exception as err:
            print(f"    Failed running pip on {py}: {err}")

    # 2. Check metadata in index.scip
    scip_file = Path("cartog-out/click-map-scip/.cartog/scip/281f030a7dc8/index.scip")
    if scip_file.is_file():
        idx = Index()
        with open(scip_file, "rb") as f:
            idx.ParseFromString(f.read())
        print("\nSCIP Index Metadata for click-map-scip:")
        meta = idx.metadata
        print(f"  version: {meta.version}")
        print(f"  tool_info: name={meta.tool_info.name}, version={meta.tool_info.version}, arguments={list(meta.tool_info.arguments)}")
        print(f"  project_root: {meta.project_root}")
        print(f"  text_document_encoding: {meta.text_document_encoding}")

    # 3. Check scip-python index --help using the Node shim
    shim_path = (Path("cartog/scip/windows_shim.js")).resolve()
    env = os.environ.copy()
    env["NODE_OPTIONS"] = f'-r "{shim_path.as_posix()}"'
    try:
        help_res = subprocess.run(["scip-python", "index", "--help"], capture_output=True, text=True, shell=True, env=env)
        print(f"\nscip-python index --help (exit {help_res.returncode}):")
        print(help_res.stdout)
        if help_res.stderr:
            print(f"stderr:\n{help_res.stderr}")
    except Exception as e:
        print(f"Failed running scip-python: {e}")


def test_classify_occurrence_ref_kinds():
    """Verify tree-sitter AST classification of occurrences into ref_kinds (callback, inheritance, type, decorator, etc.)."""
    from cartog.langs import get_adapter
    from cartog.scip_pass import classify_occurrence

    code = b"""
@my_decorator
class BaseService:
    pass

class CustomService(BaseService):
    def run(self, handler: BaseService) -> None:
        if isinstance(handler, BaseService):
            runner.invoke(cli)
"""
    py_adapter = get_adapter("python")
    tree = py_adapter.parse(code)

    # 1. Callback: 'cli' passed as argument to runner.invoke
    # Line 9: "            runner.invoke(cli)" -> col 26 is 'cli'
    kind_cb, ref_k_cb = classify_occurrence(tree, 9, 26, "python")
    assert kind_cb == "references"
    assert ref_k_cb == "callback"

    # 2. Inheritance: BaseService in CustomService(BaseService) -> line 6, col 21
    kind_inh, ref_k_inh = classify_occurrence(tree, 6, 21, "python")
    assert kind_inh == "references"
    assert ref_k_inh == "inheritance"

    # 3. Type annotation: BaseService in handler: BaseService -> line 7, col 28
    kind_typ, ref_k_typ = classify_occurrence(tree, 7, 28, "python")
    assert kind_typ == "references"
    assert ref_k_typ == "type"

    # 4. Decorator: my_decorator in @my_decorator -> line 2, col 2
    kind_dec, ref_k_dec = classify_occurrence(tree, 2, 2, "python")
    assert kind_dec == "references"
    assert ref_k_dec == "decorator"

    # 5. Isinstance: BaseService in isinstance(handler, BaseService) -> line 8, col 32
    kind_isi, ref_k_isi = classify_occurrence(tree, 8, 32, "python")
    assert kind_isi == "references"
    assert ref_k_isi == "isinstance"

    # 6. Actual call: runner.invoke(...) -> invoke at line 9, col 19
    kind_call, ref_k_call = classify_occurrence(tree, 9, 19, "python")
    assert kind_call == "calls"
    assert ref_k_call is None


def test_reconciliation_fallback_linking():
    """Verify reconciliation fallback creates candidates with confidence='reconciled' when roots match and file exists."""
    from cartog.langs.base import SymbolRecord
    from cartog.scip_pass import ScipDocument, ScipOccurrence, link_calls

    # Definition in src/click/core.py with prefix `src.click.core/Command#`
    def_sym = "scip-python python click 8.1.7 `src.click.core`/Command#"
    doc_def = ScipDocument(
        relative_path="src/click/core.py",
        language="python",
        definitions=[ScipOccurrence(symbol=def_sym, range=SourceRange(10, 0, 10, 7), is_definition=True)],
        references=[],
    )

    # Reference in tests/test_basic.py using `click.core/Command#` (without src.)
    ref_sym = "scip-python python click 8.1.7 `click.core`/Command#"
    doc_ref = ScipDocument(
        relative_path="tests/test_basic.py",
        language="python",
        definitions=[],
        references=[ScipOccurrence(symbol=ref_sym, range=SourceRange(25, 4, 25, 11), is_definition=False)],
    )

    scip_res = ScipIndexResult(
        ran=True,
        documents=[doc_def, doc_ref],
        definitions_by_symbol={def_sym: ("src/click/core.py", SourceRange(10, 0, 10, 7))},
    )

    symbols_by_file = {
        "tests/test_basic.py": [
            SymbolRecord(kind="function", name="test_cmd", qualified_name="tests.test_basic.test_cmd", start_line=20, start_col=0, end_line=30, end_col=0)
        ],
        "src/click/core.py": [
            SymbolRecord(kind="class", name="Command", qualified_name="src.click.core.Command", start_line=10, start_col=0, end_line=50, end_col=0)
        ],
    }

    candidates = link_calls(
        scip_result=scip_res,
        symbols_by_file=symbols_by_file,
        target_path="samples/click",
        roots=["src"],
        language="python",
    )

    # Should find candidate reconciled to Command in src/click/core.py
    reconciled = [c for c in candidates if c.callee_symbol == "Command"]
    assert len(reconciled) == 1
    assert reconciled[0].confidence == "reconciled"
    assert reconciled[0].caller_symbol == "test_cmd"
    assert reconciled[0].callee_qualified_name == "src.click.core.Command"
    assert reconciled[0].callee_path == "src/click/core.py"


def test_scip_reconciled_calls_through_reexport_chain(tmp_path):
    """Verify that calls through package __init__.py re-exports resolve to the defining submodule."""
    from cartog.langs.base import SymbolRecord
    from cartog.scip_pass import ScipDocument, ScipOccurrence, link_calls

    # Create directory structure in tmp_path
    src_dir = tmp_path / "src" / "mypkg"
    src_dir.mkdir(parents=True)
    tpl_file = src_dir / "templating.py"
    tpl_file.write_text("def render_template(): pass\n", encoding="utf-8")
    init_file = src_dir / "__init__.py"
    init_file.write_text("from .templating import render_template\n", encoding="utf-8")

    app_dir = tmp_path / "examples" / "demo"
    app_dir.mkdir(parents=True)
    main_file = app_dir / "main.py"
    main_file.write_text("def run():\n    render_template()\n", encoding="utf-8")

    # SCIP symbols
    def_sym = "scip-python python mypkg 1.0.0 `src.mypkg.templating`/render_template()."
    reexport_ref = "scip-python python mypkg 1.0.0 `src.mypkg.templating`/render_template()."
    call_ref = "scip-python python mypkg 1.0.0 mypkg/__init__:render_template"

    doc_sub = ScipDocument(
        relative_path="src/mypkg/templating.py",
        language="python",
        definitions=[ScipOccurrence(symbol=def_sym, range=SourceRange(1, 0, 1, 20), is_definition=True)],
        references=[],
    )
    doc_init = ScipDocument(
        relative_path="src/mypkg/__init__.py",
        language="python",
        definitions=[],
        references=[ScipOccurrence(symbol=reexport_ref, range=SourceRange(1, 25, 1, 40), is_definition=False)],
    )
    doc_main = ScipDocument(
        relative_path="examples/demo/main.py",
        language="python",
        definitions=[],
        references=[ScipOccurrence(symbol=call_ref, range=SourceRange(2, 4, 2, 19), is_definition=False)],
    )

    scip_res = ScipIndexResult(
        ran=True,
        documents=[doc_sub, doc_init, doc_main],
        definitions_by_symbol={def_sym: ("src/mypkg/templating.py", SourceRange(1, 0, 1, 20))},
    )

    symbols_by_file = {
        "src/mypkg/templating.py": [
            SymbolRecord(kind="function", name="render_template", qualified_name="src.mypkg.templating.render_template", start_line=1, start_col=0, end_line=1, end_col=25)
        ],
        "src/mypkg/__init__.py": [],
        "examples/demo/main.py": [
            SymbolRecord(kind="function", name="run", qualified_name="examples.demo.main.run", start_line=1, start_col=0, end_line=2, end_col=25)
        ],
    }

    candidates = link_calls(
        scip_result=scip_res,
        symbols_by_file=symbols_by_file,
        target_path=str(tmp_path),
        roots=["src"],
        language="python",
    )

    main_calls = [c for c in candidates if c.caller_path == "examples/demo/main.py" and c.callee_symbol == "render_template"]
    assert len(main_calls) == 1
    assert main_calls[0].confidence == "reconciled"
    assert main_calls[0].caller_symbol == "run"
    assert main_calls[0].callee_path == "src/mypkg/templating.py"
    assert main_calls[0].callee_qualified_name == "src.mypkg.templating.render_template"


def test_reconciliation_strict_prefix_matching(tmp_path):
    """Verify that reconciliation rejects mismatched package names and non-existent files without speculative bare matching."""
    from cartog.langs.base import SymbolRecord
    from cartog.scip_pass import ScipDocument, ScipOccurrence, link_calls

    # Valid definition in mypkg
    def_sym = "scip-python python mypkg 1.0.0 `src.mypkg.core`/serve()."
    core_file = tmp_path / "src" / "mypkg" / "core.py"
    core_file.parent.mkdir(parents=True)
    core_file.write_text("def serve(): pass\n", encoding="utf-8")

    # Reference with mismatched package 'otherpkg'
    ref_mismatched_pkg = "scip-python python otherpkg 1.0.0 `mypkg.core`/serve()."
    # Reference with same package but target file that doesn't exist
    ref_missing_file = "scip-python python mypkg 1.0.0 `mypkg.nonexistent`/serve()."

    doc_def = ScipDocument(
        relative_path="src/mypkg/core.py",
        language="python",
        definitions=[ScipOccurrence(symbol=def_sym, range=SourceRange(1, 0, 1, 15), is_definition=True)],
        references=[],
    )
    doc_caller = ScipDocument(
        relative_path="src/mypkg/app.py",
        language="python",
        definitions=[],
        references=[
            ScipOccurrence(symbol=ref_mismatched_pkg, range=SourceRange(2, 4, 2, 9), is_definition=False),
            ScipOccurrence(symbol=ref_missing_file, range=SourceRange(3, 4, 3, 9), is_definition=False),
        ],
    )

    scip_res = ScipIndexResult(
        ran=True,
        documents=[doc_def, doc_caller],
        definitions_by_symbol={def_sym: ("src/mypkg/core.py", SourceRange(1, 0, 1, 15))},
    )

    symbols_by_file = {
        "src/mypkg/core.py": [
            SymbolRecord(kind="function", name="serve", qualified_name="src.mypkg.core.serve", start_line=1, start_col=0, end_line=1, end_col=17)
        ],
        "src/mypkg/app.py": [
            SymbolRecord(kind="function", name="main", qualified_name="src.mypkg.app.main", start_line=1, start_col=0, end_line=4, end_col=0)
        ],
    }

    candidates = link_calls(
        scip_result=scip_res,
        symbols_by_file=symbols_by_file,
        target_path=str(tmp_path),
        roots=["src"],
        language="python",
    )

    # Neither mismatched package nor nonexistent file should produce a candidate
    assert len(candidates) == 0



