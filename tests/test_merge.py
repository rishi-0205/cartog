"""Unit tests for graph building and merging in cartog.graph.merge."""

from cartog.graph.merge import build_graph
from cartog.graph.validate import validate_graph
from cartog.parse.base import ImportRecord, ParseFileResult, SymbolRecord


def test_build_and_validate_graph():
    parsed_files = [
        ParseFileResult(
            path="src/pkg/core.py",
            language="python",
            hash="1111",
            symbols=[
                SymbolRecord(
                    kind="class",
                    name="MyClass",
                    qualified_name="pkg.core.MyClass",
                    start_line=1,
                    start_col=0,
                    end_line=10,
                    end_col=0,
                ),
                SymbolRecord(
                    kind="method",
                    name="my_method",
                    qualified_name="pkg.core.MyClass.my_method",
                    start_line=2,
                    start_col=4,
                    end_line=5,
                    end_col=10,
                    parent="MyClass",
                ),
            ],
            imports=[
                ImportRecord(
                    specifier="helper",
                    names=["assist"],
                    kind="relative",
                    level=1,
                    line=0,
                ),
                ImportRecord(
                    specifier="os",
                    names=[],
                    kind="standard",
                    level=0,
                    line=0,
                ),
            ],
        ),
        ParseFileResult(
            path="src/pkg/helper.py",
            language="python",
            hash="2222",
            symbols=[
                SymbolRecord(
                    kind="function",
                    name="assist",
                    qualified_name="pkg.helper.assist",
                    start_line=1,
                    start_col=0,
                    end_line=3,
                    end_col=10,
                )
            ],
            imports=[],
        ),
    ]

    graph = build_graph(parsed_files, target_path="test_project", roots=[".", "src"])

    # 1. Validation
    val_res = validate_graph(graph)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0

    # 2. Check Node counts
    node_kinds = [n.kind for n in graph.nodes.values()]
    assert "file" in node_kinds
    assert "folder" in node_kinds
    assert "class" in node_kinds
    assert "method" in node_kinds
    assert "function" in node_kinds
    assert "dependency" in node_kinds  # external:os

    # 3. Check Edge kinds
    edge_kinds = [e.kind for e in graph.edges]
    assert "contains" in edge_kinds
    assert "imports" in edge_kinds
    assert "depends_on" in edge_kinds

    # 4. Check specific containment
    # File core.py contains MyClass
    contains_edges = [e for e in graph.edges if e.kind == "contains"]
    assert len(contains_edges) > 0

    # 5. Check imports edge between core.py and helper.py
    import_edges = [e for e in graph.edges if e.kind == "imports"]
    assert len(import_edges) == 1
    src_node = graph.nodes[import_edges[0].source]
    tgt_node = graph.nodes[import_edges[0].target]
    assert src_node.kind == "file"
    assert tgt_node.kind == "file"

    # 6. Check depends_on edge between core.py and external os dependency
    dep_edges = [e for e in graph.edges if e.kind == "depends_on"]
    assert len(dep_edges) == 1
    dep_src = graph.nodes[dep_edges[0].source]
    dep_tgt = graph.nodes[dep_edges[0].target]
    assert dep_src.kind == "file"
    assert dep_tgt.kind == "dependency"
    assert dep_tgt.name == "os"


def test_validation_rejects_invalid_edge_endpoints():
    from cartog.core.model import Edge, Graph, Node

    # Test 1: imports edge connecting to a dependency node must fail
    g1 = Graph(schema_version="1.0.0")
    f1 = Node.create(kind="file", name="a.py", qualified_name="a.py", path="a.py")
    d1 = Node.create(kind="dependency", name="requests", qualified_name="requests")
    g1.add_node(f1)
    g1.add_node(d1)
    g1.add_edge(Edge(source=f1.id, target=d1.id, kind="imports", confidence="import"))
    res1 = validate_graph(g1)
    assert res1.is_valid is False
    assert any("must connect two file nodes" in err for err in res1.errors)

    # Test 2: depends_on edge connecting two files must fail
    g2 = Graph(schema_version="1.0.0")
    f2 = Node.create(kind="file", name="b.py", qualified_name="b.py", path="b.py")
    g2.add_node(f1)
    g2.add_node(f2)
    g2.add_edge(Edge(source=f1.id, target=f2.id, kind="depends_on", confidence="import"))
    res2 = validate_graph(g2)
    assert res2.is_valid is False
    assert any("must connect file to dependency" in err for err in res2.errors)


def test_build_graph_with_scip_calls():
    """Verify build_graph integrates SCIP call edges and passes full graph validation."""
    from pathlib import Path

    import pytest

    from cartog.parse import parse_source_file
    from cartog.scan import walk_files
    from cartog.scip.runner import decode_scip_index

    fixture_scip = Path("tests/fixtures/prebuilt_scip/index.scip")
    if not fixture_scip.is_file():
        pytest.skip("prebuilt index.scip fixture not found")

    scip_res = decode_scip_index(fixture_scip)
    scan_res = walk_files("tests/fixtures/ts_monorepo")
    parsed_files = [parse_source_file(f) for f in scan_res.files]

    graph = build_graph(
        parsed_files=parsed_files,
        target_path="tests/fixtures/ts_monorepo",
        roots=scan_res.roots,
        skipped_files=scan_res.skipped,
        scip_result=scip_res,
    )

    val_res = validate_graph(graph)
    assert val_res.is_valid is True, f"Validation errors: {val_res.errors}"

    calls_edges = [e for e in graph.edges if e.kind == "calls"]
    assert len(calls_edges) > 0
    assert any(e.confidence == "resolved" for e in calls_edges)
    assert any(e.count >= 1 for e in calls_edges)


def test_route_handler_resolution_same_named_functions_different_scopes():
    """Verify that multiple same-named handlers in different scopes link to their respective routes and parents."""
    from cartog.core.model import make_node_id

    # Two handlers named 'handler' defined before their respective routes (common in JS/Express and Python)
    s_h1 = SymbolRecord(
        kind="function",
        name="handler",
        qualified_name="api.admin_scope.handler",
        start_line=4,
        start_col=0,
        end_line=7,
        end_col=0,
    )
    s_h2 = SymbolRecord(
        kind="function",
        name="handler",
        qualified_name="api.user_scope.handler",
        start_line=24,
        start_col=0,
        end_line=27,
        end_col=0,
    )

    # Two same-named classes 'Config' in different scopes, each containing method 'get'
    c1 = SymbolRecord(
        kind="class",
        name="Config",
        qualified_name="api.Admin.Config",
        start_line=10,
        start_col=0,
        end_line=18,
        end_col=0,
    )
    m1 = SymbolRecord(
        kind="method",
        name="get",
        qualified_name="api.Admin.Config.get",
        start_line=12,
        start_col=4,
        end_line=15,
        end_col=0,
        parent="Config",
    )
    c2 = SymbolRecord(
        kind="class",
        name="Config",
        qualified_name="api.User.Config",
        start_line=40,
        start_col=0,
        end_line=48,
        end_col=0,
    )
    m2 = SymbolRecord(
        kind="method",
        name="get",
        qualified_name="api.User.Config.get",
        start_line=42,
        start_col=4,
        end_line=45,
        end_col=0,
        parent="Config",
    )

    pat1 = {
        "kind": "route",
        "name": "GET /admin",
        "url_path": "/admin",
        "methods": ["GET"],
        "handler": "handler",
        "range": [8, 0, 8, 25],
    }
    pat2 = {
        "kind": "route",
        "name": "GET /user",
        "url_path": "/user",
        "methods": ["GET"],
        "handler": "handler",
        "range": [28, 0, 28, 25],
    }

    parsed_file = ParseFileResult(
        path="src/api.py",
        language="python",
        hash="hash1",
        symbols=[s_h1, c1, m1, s_h2, c2, m2],
        imports=[],
        patterns=[pat1, pat2],
    )

    graph = build_graph([parsed_file], target_path=".")

    # 1. Verify route serves edges connect to the closest respective handlers
    serves_edges = [e for e in graph.edges if e.kind == "serves"]
    assert len(serves_edges) == 2, f"Expected 2 serves edges, got {len(serves_edges)}"

    h1_node_id = make_node_id("function", "src/api.py", "api.admin_scope.handler")
    h2_node_id = make_node_id("function", "src/api.py", "api.user_scope.handler")

    r1_node = next(n for n in graph.nodes.values() if n.kind == "route" and n.name == "GET /admin")
    r2_node = next(n for n in graph.nodes.values() if n.kind == "route" and n.name == "GET /user")

    r1_target = next(e.target for e in serves_edges if e.source == r1_node.id)
    r2_target = next(e.target for e in serves_edges if e.source == r2_node.id)

    assert r1_target == h1_node_id, f"Route 1 should link to admin handler {h1_node_id}, got {r1_target}"
    assert r2_target == h2_node_id, f"Route 2 should link to user handler {h2_node_id}, got {r2_target}"

    # 2. Verify parent containment for same-named classes does not cross-pollinate
    c1_id = make_node_id("class", "src/api.py", "api.Admin.Config")
    c2_id = make_node_id("class", "src/api.py", "api.User.Config")
    m1_node = graph.nodes[make_node_id("method", "src/api.py", "api.Admin.Config.get")]
    m2_node = graph.nodes[make_node_id("method", "src/api.py", "api.User.Config.get")]

    assert m1_node.parent == c1_id, f"Admin Config.get parent should be {c1_id}, got {m1_node.parent}"
    assert m2_node.parent == c2_id, f"User Config.get parent should be {c2_id}, got {m2_node.parent}"


def test_symbol_mapping_no_flat_name_collisions():
    """Verify SCIP candidate caller/callee resolution uses line range and avoids flat name collisions."""
    from cartog.core.model import make_node_id
    from cartog.scip.runner import CallEdgeCandidate, ScipDocument, ScipIndexResult

    s1 = SymbolRecord(
        kind="function",
        name="validate",
        qualified_name="app.validate",
        start_line=5,
        start_col=0,
        end_line=15,
        end_col=0,
    )
    s2 = SymbolRecord(
        kind="method",
        name="validate",
        qualified_name="app.Checker.validate",
        start_line=30,
        start_col=4,
        end_line=45,
        end_col=0,
    )
    s_target = SymbolRecord(
        kind="function",
        name="check_core",
        qualified_name="core.check_core",
        start_line=1,
        start_col=0,
        end_line=10,
        end_col=0,
    )

    parsed_app = ParseFileResult(
        path="src/app.py",
        language="python",
        hash="hash_app",
        symbols=[s1, s2],
        imports=[],
    )
    parsed_core = ParseFileResult(
        path="src/core.py",
        language="python",
        hash="hash_core",
        symbols=[s_target],
        imports=[],
    )

    # Candidate has caller_symbol="validate" (without qualified name) but evidence specifies line 35
    cand = CallEdgeCandidate(
        caller_path="src/app.py",
        caller_symbol="validate",
        caller_qualified_name=None,
        callee_path="src/core.py",
        callee_symbol="check_core",
        callee_qualified_name="core.check_core",
        evidence=["src/app.py:35"],
        count=1,
        kind="calls",
    )

    scip_res = ScipIndexResult(
        ran=True,
        documents=[ScipDocument(relative_path="src/app.py", language="python")],
        definitions_by_symbol={},
        relationships=[],
    )

    # Monkeypatch link_calls where merge imports it: cartog.scip.runner
    import cartog.scip.runner as scip_runner_mod
    orig_link = scip_runner_mod.link_calls
    try:
        scip_runner_mod.link_calls = lambda *args, **kwargs: [cand]
        graph = build_graph([parsed_app, parsed_core], target_path=".", scip_result=scip_res)
    finally:
        scip_runner_mod.link_calls = orig_link

    call_edges = [e for e in graph.edges if e.kind == "calls"]
    assert len(call_edges) == 1

    expected_caller_id = make_node_id("method", "src/app.py", "app.Checker.validate")
    assert call_edges[0].source == expected_caller_id, (
        f"Expected caller to be Checker.validate ({expected_caller_id}) by line 35, "
        f"got {call_edges[0].source}"
    )



