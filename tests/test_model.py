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
    assert reloaded.schema_version == "2.0.0"
    assert len(reloaded.nodes) == 2
    assert len(reloaded.edges) == 1
    assert reloaded.get_node(n1.id) is not None
    assert reloaded.get_node(n2.id).name == "foo"
    assert reloaded.stats.get("total_nodes") == 2
    assert reloaded.stats.get("total_edges") == 1


def _edge(source: str, target: str, kind: str = "calls", **kwargs) -> Edge:
    return Edge(source=source, target=target, kind=kind, confidence="resolved", **kwargs)


def test_edge_index_tracks_edges():
    """F5: add_edge keeps a keyed index in sync with the edge list."""
    graph = Graph()
    graph.add_edge(_edge("a", "b", count=1))
    graph.add_edge(_edge("c", "d", count=2))
    graph.add_edge(_edge("a", "b", count=3))

    assert len(graph.edges) == 2
    assert {(e.source, e.target, e.kind) for e in graph.edges} == {
        ("a", "b", "calls"),
        ("c", "d", "calls"),
    }
    assert len(graph._edge_index) == len(graph.edges)
    assert set(graph._edge_index) == {(e.source, e.target, e.kind) for e in graph.edges}
    for edge in graph.edges:
        assert graph._edge_index[(edge.source, edge.target, edge.kind)] is edge


def test_add_edge_aggregates_and_preserves_order():
    """Aggregation merges counts, evidence, and imported names without reordering."""
    graph = Graph()
    graph.add_edge(_edge("a", "b", count=1, evidence=["x.py:1"],
                         attrs={"imported_names": ["one"]}))
    graph.add_edge(_edge("c", "d", count=4))
    graph.add_edge(_edge("a", "b", count=2, evidence=["y.py:2"],
                         attrs={"imported_names": ["two", "one"]}))

    assert [(e.source, e.target) for e in graph.edges] == [("a", "b"), ("c", "d")]
    merged = graph.edges[0]
    assert merged.count == 3
    assert merged.evidence == ["x.py:1", "y.py:2"]
    assert merged.attrs["imported_names"] == ["one", "two"]


def test_edge_index_survives_external_list_mutation():
    """An external `edges.clear()` must not leave stale index entries."""
    graph = Graph()
    graph.add_edge(_edge("a", "b", count=5))
    graph.edges.clear()
    graph.add_edge(_edge("a", "b", count=1))

    assert len(graph.edges) == 1
    assert graph.edges[0].count == 1


def test_edge_index_does_not_change_serialized_output():
    """Round-tripping a graph must produce identical JSON, byte for byte."""
    graph = Graph(meta={"target_path": "serialization"})
    n1 = Node.create(kind="function", name="a", qualified_name="m.py:a", path="m.py")
    n2 = Node.create(kind="function", name="b", qualified_name="m.py:b", path="m.py")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(_edge(n1.id, n2.id, count=1, evidence=["m.py:1"],
                         attrs={"imported_names": ["b"]}))
    graph.add_edge(_edge(n1.id, n2.id, count=2, evidence=["m.py:2"]))

    payload = graph.to_json()
    reloaded = Graph.from_dict(graph.to_dict())
    assert reloaded.to_json() == payload
    assert len(reloaded.edges) == 1
    assert reloaded.edges[0].count == 3
