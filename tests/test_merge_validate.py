"""Tests for graph validation extensions: range integrity, containment, and cross-checking."""

import pytest
from pathlib import Path

from cartog.model import Edge, Graph, Node, SourceRange
from cartog.validate import (
    cross_check_imports_and_calls,
    validate_graph,
    validate_ranges_and_containment,
)


def _make_minimal_graph() -> Graph:
    return Graph(
        schema_version="1.0.0",
        meta={"tool_version": "0.1.0"},
        nodes={},
        edges=[],
        skipped=[],
    )


def test_1based_coordinate_validation():
    """Verify validate_ranges_and_containment catches 0-based or negative coordinates."""
    graph = _make_minimal_graph()
    f_node = Node.create(kind="file", name="test.py", qualified_name="test.py", path="test.py")
    graph.add_node(f_node)

    # 1. Valid 1-based node range
    valid_func = Node.create(
        kind="function",
        name="foo",
        qualified_name="test.foo",
        path="test.py",
        range=SourceRange(1, 0, 10, 0),
    )
    graph.add_node(valid_func)
    res = validate_ranges_and_containment(graph)
    assert res.is_valid
    assert len(res.errors) == 0

    # 2. Invalid 0-based node start_line
    bad_func = Node.create(
        kind="function",
        name="bad",
        qualified_name="test.bad",
        path="test.py",
        range=SourceRange(0, 0, 5, 0),
    )
    graph.add_node(bad_func)
    res_bad = validate_ranges_and_containment(graph)
    assert not res_bad.is_valid
    assert any("0-based" in e for e in res_bad.errors)

    # 3. Invalid 0-based edge evidence
    graph.nodes.pop(bad_func.id)
    graph.add_edge(
        Edge(
            source=valid_func.id,
            target=valid_func.id,
            kind="references",
            confidence="resolved",
            evidence=["test.py:0"],
        )
    )
    res_ev = validate_ranges_and_containment(graph)
    assert not res_ev.is_valid
    assert any("0-based" in e for e in res_ev.errors)


def test_physical_file_length_validation(tmp_path):
    """Verify node and evidence line numbers cannot exceed physical file lengths on disk."""
    repo = tmp_path / "repo"
    repo.mkdir()
    py_file = repo / "module.py"
    py_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    graph = _make_minimal_graph()
    f_node = Node.create(kind="file", name="module.py", qualified_name="module.py", path="module.py")
    graph.add_node(f_node)

    # Node exceeding physical 5 lines
    too_long = Node.create(
        kind="function",
        name="long_fn",
        qualified_name="module.long_fn",
        path="module.py",
        range=SourceRange(2, 0, 12, 0),
    )
    graph.add_node(too_long)

    res = validate_ranges_and_containment(graph, target_path=str(repo))
    assert not res.is_valid
    assert any("exceeds physical file length 5" in e for e in res.errors)


def test_caller_range_containment():
    """Verify call evidence lines must fall inside the caller function's line range."""
    graph = _make_minimal_graph()
    f1 = Node.create(kind="file", name="f1.py", qualified_name="f1.py", path="f1.py")
    f2 = Node.create(kind="file", name="f2.py", qualified_name="f2.py", path="f2.py")
    graph.add_node(f1)
    graph.add_node(f2)

    caller = Node.create(
        kind="function",
        name="caller_fn",
        qualified_name="f1.caller_fn",
        path="f1.py",
        range=SourceRange(10, 0, 30, 0),
    )
    callee = Node.create(
        kind="function",
        name="callee_fn",
        qualified_name="f2.callee_fn",
        path="f2.py",
        range=SourceRange(1, 0, 10, 0),
    )
    graph.add_node(caller)
    graph.add_node(callee)

    # Valid call evidence line inside [10, 30]
    valid_edge = Edge(
        source=caller.id,
        target=callee.id,
        kind="calls",
        confidence="resolved",
        evidence=["f1.py:20"],
    )
    graph.add_edge(valid_edge)
    res_valid = validate_ranges_and_containment(graph)
    assert res_valid.is_valid

    # Invalid call evidence line outside [10, 30]
    bad_edge = Edge(
        source=caller.id,
        target=callee.id,
        kind="calls",
        confidence="resolved",
        evidence=["f1.py:35"],
    )
    graph.edges.append(bad_edge)
    res_bad = validate_ranges_and_containment(graph)
    assert not res_bad.is_valid
    assert any("falls outside caller" in e for e in res_bad.errors)


def test_child_symbol_range_containment():
    """Verify child method/function ranges must be strictly contained within parent class range."""
    graph = _make_minimal_graph()
    f_node = Node.create(kind="file", name="cls.py", qualified_name="cls.py", path="cls.py")
    graph.add_node(f_node)

    cls_node = Node.create(
        kind="class",
        name="MyClass",
        qualified_name="cls.MyClass",
        path="cls.py",
        range=SourceRange(10, 0, 50, 0),
    )
    good_method = Node.create(
        kind="method",
        name="m1",
        qualified_name="cls.MyClass.m1",
        path="cls.py",
        range=SourceRange(15, 4, 30, 20),
    )
    bad_method = Node.create(
        kind="method",
        name="m2",
        qualified_name="cls.MyClass.m2",
        path="cls.py",
        range=SourceRange(5, 4, 25, 20),  # starts before parent class
    )
    graph.add_node(cls_node)
    graph.add_node(good_method)
    graph.add_node(bad_method)

    graph.add_edge(Edge(source=cls_node.id, target=good_method.id, kind="contains", confidence="resolved"))
    res_good = validate_ranges_and_containment(graph)
    assert res_good.is_valid

    graph.add_edge(Edge(source=cls_node.id, target=bad_method.id, kind="contains", confidence="resolved"))
    res_bad = validate_ranges_and_containment(graph)
    assert not res_bad.is_valid
    assert any("not contained within parent" in e for e in res_bad.errors)


def test_cross_check_imports_and_calls():
    """Verify cross-checker categorizes direct imports, explained mismatches, and unexplained mismatches."""
    graph = _make_minimal_graph()

    # 3 files: a.py, barrel.py, b.py
    fa = Node.create(kind="file", name="a.py", qualified_name="src/a.py", path="src/a.py")
    fb = Node.create(kind="file", name="b.py", qualified_name="src/b.py", path="src/b.py")
    f_barrel = Node.create(kind="file", name="__init__.py", qualified_name="src/__init__.py", path="src/__init__.py")
    f_other = Node.create(kind="file", name="other.py", qualified_name="other.py", path="other.py")

    for f in (fa, fb, f_barrel, f_other):
        graph.add_node(f)

    fn_a = Node.create(kind="function", name="call_b", qualified_name="src.a.call_b", path="src/a.py")
    fn_b = Node.create(kind="function", name="target_b", qualified_name="src.b.target_b", path="src/b.py")
    fn_other = Node.create(kind="function", name="fn_other", qualified_name="other.fn_other", path="other.py")

    for fn in (fn_a, fn_b, fn_other):
        graph.add_node(fn)

    # 1. Direct import: a.py imports b.py
    graph.add_edge(Edge(source=fa.id, target=fb.id, kind="imports", confidence="import"))
    graph.add_edge(Edge(source=fn_a.id, target=fn_b.id, kind="calls", confidence="resolved", evidence=["src/a.py:5"]))

    res1 = cross_check_imports_and_calls(graph)
    assert res1.total_cross_file_calls == 1
    assert res1.matched_calls == 1
    assert len(res1.explained_mismatches) == 0
    assert len(res1.unexplained_mismatches) == 0
    assert res1.is_clean

    # 2. Transitive / barrel import: a.py imports __init__.py, __init__.py imports b.py (remove direct a -> b)
    graph.edges.clear()
    graph.add_edge(Edge(source=fa.id, target=f_barrel.id, kind="imports", confidence="import"))
    graph.add_edge(Edge(source=f_barrel.id, target=fb.id, kind="imports", confidence="import"))
    graph.add_edge(Edge(source=fn_a.id, target=fn_b.id, kind="calls", confidence="resolved", evidence=["src/a.py:5"]))

    res2 = cross_check_imports_and_calls(graph)
    assert res2.total_cross_file_calls == 1
    assert res2.matched_calls == 0
    assert len(res2.explained_mismatches) == 1
    assert res2.explained_mismatches[0].category == "explained"
    assert "barrel" in res2.explained_mismatches[0].reason
    assert res2.is_clean

    # 3. Unexplained mismatch: other.py calls b.py with no import relationship
    graph.add_edge(Edge(source=fn_other.id, target=fn_b.id, kind="calls", confidence="resolved", evidence=["other.py:10"]))
    res3 = cross_check_imports_and_calls(graph)
    assert res3.total_cross_file_calls == 2
    assert len(res3.unexplained_mismatches) == 1
    assert res3.unexplained_mismatches[0].category == "unexplained"
    assert not res3.is_clean


def test_validation_rejects_dangling_edge():
    """Verify validation reports an error when an edge references a missing node."""
    graph = _make_minimal_graph()
    fn = Node.create(kind="function", name="f", qualified_name="mod.f", path="mod.py")
    graph.add_node(fn)
    # Dangling target
    graph.add_edge(Edge(source=fn.id, target="non_existent_node_id", kind="calls", confidence="resolved"))
    res = validate_graph(graph)
    assert not res.is_valid
    assert any("Dangling edge target" in e for e in res.errors)


def test_validation_rejects_duplicate_node_id():
    """Verify validation reports an error if duplicate node IDs are detected."""
    graph_data = {
        "schema_version": "2.0.0",
        "nodes": [
            {"id": "duplicate12", "kind": "file", "name": "a.py", "qualified_name": "a.py"},
            {"id": "duplicate12", "kind": "file", "name": "b.py", "qualified_name": "b.py"},
        ],
        "edges": [],
    }
    graph = Graph.from_dict(graph_data)
    res = validate_graph(graph)
    assert not res.is_valid
    assert any("Duplicate node id" in e for e in res.errors)


def test_validation_rejects_file_with_two_parents():
    """Verify validation reports an error if a node/file has multiple parents."""
    graph = _make_minimal_graph()
    folder1 = Node.create(kind="file", name="dir1", qualified_name="dir1", path="dir1")
    folder2 = Node.create(kind="file", name="dir2", qualified_name="dir2", path="dir2")
    file_node = Node.create(kind="file", name="sub.py", qualified_name="dir1/sub.py", path="dir1/sub.py")
    for n in (folder1, folder2, file_node):
        graph.add_node(n)

    # Add two incoming contains edges
    graph.add_edge(Edge(source=folder1.id, target=file_node.id, kind="contains", confidence="resolved"))
    graph.add_edge(Edge(source=folder2.id, target=file_node.id, kind="contains", confidence="resolved"))

    res = validate_graph(graph)
    assert not res.is_valid
    assert any("multiple parents" in e.lower() for e in res.errors)


def test_validation_rejects_call_evidence_outside_caller_range():
    """Verify validation rejects call edges whose evidence line falls outside the caller's range or in wrong file."""
    graph = _make_minimal_graph()
    f1 = Node.create(kind="file", name="f1.py", qualified_name="f1.py", path="f1.py")
    f2 = Node.create(kind="file", name="f2.py", qualified_name="f2.py", path="f2.py")
    caller = Node.create(
        kind="function",
        name="caller_fn",
        qualified_name="f1.caller_fn",
        path="f1.py",
        range=SourceRange(10, 0, 20, 0),
    )
    callee = Node.create(
        kind="function",
        name="callee_fn",
        qualified_name="f2.callee_fn",
        path="f2.py",
        range=SourceRange(1, 0, 10, 0),
    )
    for n in (f1, f2, caller, callee):
        graph.add_node(n)

    # Evidence line 25 falls outside [10, 20]
    bad_edge = Edge(
        source=caller.id,
        target=callee.id,
        kind="calls",
        confidence="resolved",
        evidence=["f1.py:25"],
    )
    graph.add_edge(bad_edge)

    res = validate_ranges_and_containment(graph)
    assert not res.is_valid
    assert any("falls outside caller" in e for e in res.errors)


def test_validation_rejects_route_with_multiple_handlers():
    """Verify validation reports an error if a route node is linked to more than one handler function."""
    graph = _make_minimal_graph()
    f = Node.create(kind="file", name="app.py", qualified_name="app.py", path="app.py")
    route = Node.create(kind="route", name="GET /", qualified_name="app.py:10:GET /", path="app.py")
    h1 = Node.create(kind="function", name="handler_one", qualified_name="app.handler_one", path="app.py")
    h2 = Node.create(kind="function", name="handler_two", qualified_name="app.handler_two", path="app.py")
    for n in (f, route, h1, h2):
        graph.add_node(n)

    graph.add_edge(Edge(source=route.id, target=h1.id, kind="serves", confidence="resolved"))
    graph.add_edge(Edge(source=route.id, target=h2.id, kind="serves", confidence="resolved"))

    res = validate_graph(graph)
    assert not res.is_valid
    assert any("multiple" in e.lower() and "serves" in e.lower() for e in res.errors)


def test_validation_rejects_cyclic_parent_chain():
    """Verify validation detects cyclic parent relationships across nodes."""
    graph = _make_minimal_graph()
    n1 = Node.create(kind="class", name="A", qualified_name="A", path="a.py")
    n2 = Node.create(kind="class", name="B", qualified_name="B", path="b.py")
    n1.parent = n2.id
    n2.parent = n1.id
    graph.add_node(n1)
    graph.add_node(n2)

    res = validate_graph(graph)
    assert not res.is_valid
    assert any("Cycle detected" in e for e in res.errors)


def test_validation_rejects_aggregated_edge_count_mismatch():
    """Verify validation reports an error when an aggregated edge count does not equal underlying edges."""
    graph = _make_minimal_graph()
    f1 = Node.create(kind="file", name="f1.py", qualified_name="f1.py", path="f1.py")
    f2 = Node.create(kind="file", name="f2.py", qualified_name="f2.py", path="f2.py")
    graph.add_node(f1)
    graph.add_node(f2)

    # Aggregated edge declares count=10, but underlying edges attribute indicates mismatch
    agg_edge = Edge(
        source=f1.id,
        target=f2.id,
        kind="calls",
        confidence="resolved",
        count=10,
    )
    agg_edge.attrs = {"aggregated": True, "underlying_count": 4}
    graph.add_edge(agg_edge)

    res = validate_graph(graph)
    assert not res.is_valid
    assert any("aggregated" in e.lower() and "count" in e.lower() for e in res.errors)


def test_validation_no_hardcoded_paths():
    """Verify cartog/validate.py contains no hardcoded absolute or sample repo paths."""
    val_file = Path(__file__).resolve().parent.parent / "cartog" / "validate.py"
    text = val_file.read_text(encoding="utf-8")
    assert "src/click/exceptions.py" not in text
    assert "src/click/types.py" not in text

