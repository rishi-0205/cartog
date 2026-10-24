"""Unit tests for Mermaid diagram generation in cartog.export_mermaid."""

from cartog.export_mermaid import generate_overview_mermaid, sanitize_id, sanitize_label
from cartog.model import Edge, Graph, Node


def test_sanitize_helpers():
    assert sanitize_id("foo/bar-baz.py") == "foo_bar_baz_py"
    assert sanitize_label('hello "world" [test]') == 'hello \\"world\\" (test)'


def test_generate_overview_mermaid():
    graph = Graph()

    f1 = Node.create(kind="file", name="core.py", qualified_name="click/core.py", path="click/core.py")
    f2 = Node.create(kind="file", name="parser.py", qualified_name="click/parser.py", path="click/parser.py")
    f3 = Node.create(kind="file", name="main.py", qualified_name="main.py", path="main.py")

    graph.add_node(f1)
    graph.add_node(f2)
    graph.add_node(f3)

    e1 = Edge(source=f1.id, target=f2.id, kind="imports", confidence="import")
    graph.add_edge(e1)

    mmd = generate_overview_mermaid(graph, direction="TD")

    assert "flowchart TD" in mmd
    assert "subgraph" in mmd
    assert "core.py" in mmd
    assert "parser.py" in mmd
    assert "main.py" in mmd
    assert "-->" in mmd


def test_mermaid_source_expanded_tests_collapsed():
    graph = Graph()

    # Source files
    s1 = Node.create(kind="file", name="core.py", qualified_name="src.pkg.core", path="src/pkg/core.py")
    s2 = Node.create(kind="file", name="utils.py", qualified_name="src.pkg.utils", path="src/pkg/utils.py")
    # Test files
    t1 = Node.create(kind="file", name="test_core.py", qualified_name="tests.test_core", path="tests/test_core.py")
    t2 = Node.create(kind="file", name="test_utils.py", qualified_name="tests.test_utils", path="tests/test_utils.py")

    graph.add_node(s1)
    graph.add_node(s2)
    graph.add_node(t1)
    graph.add_node(t2)

    # Edge from test to source
    graph.add_edge(Edge(source=t1.id, target=s1.id, kind="imports", confidence="import", count=2))
    # Edge between source files
    graph.add_edge(Edge(source=s1.id, target=s2.id, kind="imports", confidence="import", count=1))

    mmd = generate_overview_mermaid(graph)

    # Source must be expanded
    assert "subgraph" in mmd
    assert "core.py" in mmd
    assert "utils.py" in mmd

    # Tests must be collapsed into one node
    assert "cat_tests" in mmd
    assert 'cat_tests["📁 tests (2 files)"]' in mmd
    assert "test_core.py" not in mmd
    assert "test_utils.py" not in mmd

    # Aggregated edge with count > 1 shown
    assert "-->|2|" in mmd


def test_mermaid_collapsed_folder_internal_edges_label():
    graph = Graph()

    t1 = Node.create(kind="file", name="test_a.py", qualified_name="tests.test_a", path="tests/test_a.py")
    t2 = Node.create(kind="file", name="test_b.py", qualified_name="tests.test_b", path="tests/test_b.py")
    graph.add_node(t1)
    graph.add_node(t2)

    # Internal edge between test files
    graph.add_edge(Edge(source=t1.id, target=t2.id, kind="imports", confidence="import", count=3))

    mmd = generate_overview_mermaid(graph)

    # Collapsed tests label must summarize internal imports count
    assert "cat_tests" in mmd
    assert "tests (2 files, 3 internal imports)" in mmd


def test_mermaid_edge_combinations_calls_and_imports():
    """Verify all four edge combinations between expanded files:
    1. Both calls and imports (solid line, combined label: 'X calls, Y imports')
    2. Only calls (dashed line '-.-' / '-.->', label: 'X calls')
    3. Only calls singular (dashed line '-.-' / '-.->', label: '1 call')
    4. Only imports (solid line '-->', count if > 1)
    """
    graph = Graph()
    f1 = Node.create(kind="file", name="alpha.py", qualified_name="src.pkg.alpha", path="src/pkg/alpha.py")
    f2 = Node.create(kind="file", name="beta.py", qualified_name="src.pkg.beta", path="src/pkg/beta.py")
    f3 = Node.create(kind="file", name="gamma.py", qualified_name="src.pkg.gamma", path="src/pkg/gamma.py")
    f4 = Node.create(kind="file", name="delta.py", qualified_name="src.pkg.delta", path="src/pkg/delta.py")

    for f in (f1, f2, f3, f4):
        graph.add_node(f)

    # 1. Both calls (3) and imports (2)
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="imports", confidence="import", count=2))
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="calls", confidence="resolved", count=3))

    # 2. Only calls (4)
    graph.add_edge(Edge(source=f2.id, target=f3.id, kind="calls", confidence="resolved", count=4))

    # 3. Only calls (1)
    graph.add_edge(Edge(source=f3.id, target=f4.id, kind="calls", confidence="resolved", count=1))

    # 4. Only imports (single) and (multiple)
    graph.add_edge(Edge(source=f4.id, target=f1.id, kind="imports", confidence="import", count=1))
    graph.add_edge(Edge(source=f1.id, target=f3.id, kind="imports", confidence="import", count=5))

    mmd = generate_overview_mermaid(graph)

    # Both: solid line with combined label
    assert f"file_{f1.id} -->|3 calls, 2 imports| file_{f2.id}" in mmd

    # Only calls multiple: dashed line with calls label
    assert f"file_{f2.id} -.->|4 calls| file_{f3.id}" in mmd
    assert "-.-" in mmd  # distinct visual style dashed line

    # Only calls singular: dashed line with 1 call label
    assert f"file_{f3.id} -.->|1 call| file_{f4.id}" in mmd

    # Only imports single: solid line without count
    assert f"file_{f4.id} --> file_{f1.id}" in mmd

    # Only imports multiple: solid line with count
    assert f"file_{f1.id} -->|5| file_{f3.id}" in mmd


def test_mermaid_collapsed_folder_internal_calls_and_imports():
    """Verify collapsed folder internal summaries include both calls and imports."""
    graph = Graph()

    t1 = Node.create(kind="file", name="test_x.py", qualified_name="tests.test_x", path="tests/test_x.py")
    t2 = Node.create(kind="file", name="test_y.py", qualified_name="tests.test_y", path="tests/test_y.py")
    graph.add_node(t1)
    graph.add_node(t2)

    graph.add_edge(Edge(source=t1.id, target=t2.id, kind="calls", confidence="resolved", count=8))
    graph.add_edge(Edge(source=t1.id, target=t2.id, kind="imports", confidence="import", count=3))

    mmd = generate_overview_mermaid(graph)

    assert "cat_tests" in mmd
    assert "tests (2 files, 8 internal calls, 3 internal imports)" in mmd


def test_mermaid_function_level_calls_attributed_to_files():
    """Verify that calls between function/method nodes are correctly mapped to their enclosing files."""
    graph = Graph()

    f1 = Node.create(kind="file", name="caller.py", qualified_name="src.pkg.caller", path="src/pkg/caller.py")
    f2 = Node.create(kind="file", name="callee.py", qualified_name="src.pkg.callee", path="src/pkg/callee.py")
    fn1 = Node.create(kind="function", name="do_work", qualified_name="src.pkg.caller.do_work", path="src/pkg/caller.py")
    fn2 = Node.create(kind="function", name="helper", qualified_name="src.pkg.callee.helper", path="src/pkg/callee.py")

    for n in (f1, f2, fn1, fn2):
        graph.add_node(n)

    # Function-level call
    graph.add_edge(Edge(source=fn1.id, target=fn2.id, kind="calls", confidence="resolved", count=6))
    # File-level import
    graph.add_edge(Edge(source=f1.id, target=f2.id, kind="imports", confidence="import", count=1))

    mmd = generate_overview_mermaid(graph)

    assert f"file_{f1.id} -->|6 calls, 1 import| file_{f2.id}" in mmd


