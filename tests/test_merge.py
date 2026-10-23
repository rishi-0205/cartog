"""Unit tests for graph building and merging in cartog.merge."""

from cartog.langs.base import ImportRecord, ParseFileResult, SymbolRecord
from cartog.merge import build_graph
from cartog.validate import validate_graph


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
    from cartog.model import Edge, Graph, Node

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

