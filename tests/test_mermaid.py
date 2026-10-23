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

