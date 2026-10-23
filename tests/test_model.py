"""Unit tests for cartog.model."""

from pathlib import Path
from cartog.model import Edge, Graph, Node, SourceRange, make_edge_id, make_node_id


def test_node_id_stability():
    id1 = make_node_id("function", "cartog/cli.py", "main")
    id2 = make_node_id("function", "cartog/cli.py", "main")
    id3 = make_node_id("function", "cartog/cli.py", "version")

    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 10


def test_edge_id_stability():
    eid1 = make_edge_id("nodeA", "nodeB", "imports")
    eid2 = make_edge_id("nodeA", "nodeB", "imports")
    eid3 = make_edge_id("nodeA", "nodeB", "calls")

    assert eid1 == eid2
    assert eid1 != eid3
    assert len(eid1) == 10


def test_graph_serialization(tmp_path: Path):
    graph = Graph(meta={"target_path": "test_repo", "languages": ["python"]})

    n1 = Node.create(kind="file", name="a.py", qualified_name="a.py", path="a.py")
    n2 = Node.create(
        kind="function",
        name="foo",
        qualified_name="a.foo",
        path="a.py",
        range=SourceRange(0, 0, 5, 10),
    )
    graph.add_node(n1)
    graph.add_node(n2)

    e1 = Edge(source=n1.id, target=n2.id, kind="contains", confidence="resolved")
    graph.add_edge(e1)

    # Save to JSON
    json_path = tmp_path / "graph.json"
    graph.save(json_path)
    assert json_path.exists()

    # Reload and verify
    reloaded = Graph.load(json_path)
    assert reloaded.schema_version == "1.0.0"
    assert len(reloaded.nodes) == 2
    assert len(reloaded.edges) == 1
    assert reloaded.get_node(n1.id) is not None
    assert reloaded.get_node(n2.id).name == "foo"
    assert reloaded.stats.get("total_nodes") == 2
    assert reloaded.stats.get("total_edges") == 1
