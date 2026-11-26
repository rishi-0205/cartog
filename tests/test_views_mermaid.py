"""Unit and integration tests for Milestone 10: Universal View Model, Flow Tracing, Digest, Queries, and Schema 2.0.0."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cartog.cli import app
from cartog.core.config import SCHEMA_VERSION
from cartog.core.model import Edge, Graph, Node, SourceRange
from cartog.graph.merge import build_graph
from cartog.graph.validate import validate_graph
from cartog.parse.base import ImportRecord, ParseFileResult, SymbolRecord
from cartog.render.export_mermaid import (
    generate_flow_mermaid,
    generate_folder_mermaid,
    generate_overview_mermaid,
)
from cartog.render.views import (
    build_universal_view_tree,
    classify_boundary_functions,
    generate_digest,
    get_call_counts,
    rewire_view_edges,
    trace_call_flow,
)

runner = CliRunner()


def _make_sample_graph() -> Graph:
    """Build a synthetic graph with cross-file calls and internal helper functions."""
    g = Graph(schema_version=SCHEMA_VERSION, meta={"target_path": "synthetic_app"})

    # 1. Folder nodes
    folder_core = Node.create(kind="folder", name="core", qualified_name="src/core", path="src/core")
    folder_api = Node.create(kind="folder", name="api", qualified_name="src/api", path="src/api")
    g.add_node(folder_core)
    g.add_node(folder_api)

    # 2. File nodes
    file_engine = Node.create(
        kind="file",
        name="engine.py",
        qualified_name="src/core/engine.py",
        path="src/core/engine.py",
        language="python",
        parent=folder_core.id,
    )
    file_routes = Node.create(
        kind="file",
        name="routes.py",
        qualified_name="src/api/routes.py",
        path="src/api/routes.py",
        language="python",
        parent=folder_api.id,
    )
    g.add_node(file_engine)
    g.add_node(file_routes)

    # 3. Class in engine.py
    cls_engine = Node.create(
        kind="class",
        name="Engine",
        qualified_name="src/core/engine.py:Engine",
        path="src/core/engine.py",
        parent=file_engine.id,
        range=SourceRange(1, 0, 30, 0),
    )
    g.add_node(cls_engine)

    # Methods in Engine: one boundary method, two internal helpers
    meth_run = Node.create(
        kind="method",
        name="run",
        qualified_name="src/core/engine.py:Engine.run",
        path="src/core/engine.py",
        parent=cls_engine.id,
        range=SourceRange(2, 4, 10, 0),
    )
    meth_step1 = Node.create(
        kind="method",
        name="_step1",
        qualified_name="src/core/engine.py:Engine._step1",
        path="src/core/engine.py",
        parent=cls_engine.id,
        range=SourceRange(11, 4, 15, 0),
    )
    meth_step2 = Node.create(
        kind="method",
        name="_step2",
        qualified_name="src/core/engine.py:Engine._step2",
        path="src/core/engine.py",
        parent=cls_engine.id,
        range=SourceRange(16, 4, 20, 0),
    )
    g.add_node(meth_run)
    g.add_node(meth_step1)
    g.add_node(meth_step2)

    # Module-level internal helper in engine.py
    fn_util = Node.create(
        kind="function",
        name="_internal_calc",
        qualified_name="src/core/engine.py:_internal_calc",
        path="src/core/engine.py",
        parent=file_engine.id,
        range=SourceRange(22, 0, 25, 0),
    )
    g.add_node(fn_util)

    # 4. Route and handler in routes.py
    route_index = Node.create(
        kind="route",
        name="GET /status",
        qualified_name="src/api/routes.py:GET /status",
        path="src/api/routes.py",
        parent=file_routes.id,
        attrs={"handler": "status_handler"},
    )
    fn_handler = Node.create(
        kind="function",
        name="status_handler",
        qualified_name="src/api/routes.py:status_handler",
        path="src/api/routes.py",
        parent=file_routes.id,
        range=SourceRange(5, 0, 15, 0),
    )
    g.add_node(route_index)
    g.add_node(fn_handler)

    # 5. Edges
    # Route serves handler
    g.add_edge(Edge(source=route_index.id, target=fn_handler.id, kind="serves", confidence="resolved"))
    # status_handler calls Engine.run (cross-file call!)
    g.add_edge(
        Edge(
            source=fn_handler.id,
            target=meth_run.id,
            kind="calls",
            confidence="resolved",
            count=3,
            evidence=["src/api/routes.py:8"],
        )
    )
    # Engine.run calls _step1, _step2, and _internal_calc (intra-file calls!)
    g.add_edge(Edge(source=meth_run.id, target=meth_step1.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=meth_run.id, target=meth_step2.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=meth_run.id, target=fn_util.id, kind="calls", confidence="resolved"))

    return g


def test_boundary_function_classification():
    """Verify cross-file callers/callees and routes are boundary nodes; intra-file methods are helpers."""
    g = _make_sample_graph()
    boundary_ids, helper_ids = classify_boundary_functions(g)

    # GET /status is a route -> boundary
    assert any(g.nodes[bid].name == "GET /status" for bid in boundary_ids)
    # status_handler is a route handler and calls cross-file -> boundary
    assert any(g.nodes[bid].name == "status_handler" for bid in boundary_ids)
    # Engine.run is called across files -> boundary
    assert any(g.nodes[bid].name == "run" for bid in boundary_ids)

    # _step1, _step2, and _internal_calc are called only internally -> helpers
    helper_names = {g.nodes[hid].name for hid in helper_ids}
    assert "_step1" in helper_names
    assert "_step2" in helper_names
    assert "_internal_calc" in helper_names
    assert "run" not in helper_names


def test_universal_view_tree_hierarchy_and_helper_collapse():
    """Verify Universal View Model tree groups: Subsystem -> Folder -> File -> Class -> Methods + Helpers."""
    g = _make_sample_graph()
    tree = build_universal_view_tree(g)

    assert tree.kind == "subsystem"
    assert len(tree.children) == 2  # src/core and src/api folders

    core_folder = next(c for c in tree.children if "core" in c.name)
    assert core_folder.kind == "folder"
    assert len(core_folder.children) == 1
    engine_file = core_folder.children[0]
    assert engine_file.kind == "file"
    assert engine_file.name == "engine.py"

    # engine.py should contain Engine class and 1 helper group for module-level helpers
    engine_class = next(c for c in engine_file.children if c.name == "Engine")
    assert engine_class.kind == "class"

    # Engine class should have 'run' method and '+2 internal helpers' group
    class_children_names = [c.name for c in engine_class.children]
    assert "run" in class_children_names
    assert "+2 internal helpers" in class_children_names

    # File-level helper for _internal_calc
    file_helper = next(c for c in engine_file.children if c.kind == "helper_group")
    assert file_helper.name == "+1 internal helpers"


def test_compact_json_and_parent_serialization(tmp_path: Path):
    """Verify Schema 2.0.0 writes unindented JSON by default, preserves parent ID, and supports --pretty."""
    g = _make_sample_graph()
    val_res = validate_graph(g)
    assert val_res.is_valid is True

    # 1. Compact unindented serialization
    compact_path = tmp_path / "compact_graph.json"
    g.save(compact_path, pretty=False)
    compact_text = compact_path.read_text(encoding="utf-8")

    # Unindented JSON should have only 1 line
    assert compact_text.count("\n") == 0
    compact_data = json.loads(compact_text)
    assert compact_data["schema_version"] == "2.2.0"

    # Check parent ID on child nodes
    run_dict = next(n for n in compact_data["nodes"] if n["name"] == "run")
    engine_dict = next(n for n in compact_data["nodes"] if n["name"] == "Engine")
    assert run_dict.get("parent") == engine_dict["id"]

    # 2. Pretty serialization
    pretty_path = tmp_path / "pretty_graph.json"
    g.save(pretty_path, pretty=True)
    pretty_text = pretty_path.read_text(encoding="utf-8")
    assert pretty_text.count("\n") > 50

    # 3. Reload re-validates cleanly
    reloaded = Graph.load(compact_path)
    assert reloaded.schema_version == "2.2.0"
    reloaded_val = validate_graph(reloaded)
    assert reloaded_val.is_valid is True


def test_trace_call_flow_bfs():
    """Verify BFS call-flow traversal traces outgoing call chains from entrypoints and routes."""
    g = _make_sample_graph()

    # Trace from GET /status -> status_handler -> Engine.run -> _step1, _step2, _internal_calc
    visited, edges = trace_call_flow(g, target="GET /status", max_depth=3)
    visited_names = {n.name for n in visited}

    assert "GET /status" in visited_names
    assert "status_handler" in visited_names
    assert "run" in visited_names
    assert "_step1" in visited_names
    assert "_step2" in visited_names
    assert "_internal_calc" in visited_names

    # Check edge traversal count
    edge_kinds = [e.kind for e in edges]
    assert "serves" in edge_kinds
    assert "calls" in edge_kinds

    # Test Mermaid flowchart generation for flow trace
    flow_mmd = generate_flow_mermaid(visited, edges, target_name="GET /status")
    assert "flowchart LR" in flow_mmd
    assert "status_handler" in flow_mmd
    assert "Engine.run" in flow_mmd or "run()" in flow_mmd
    assert "classDef route" in flow_mmd
    assert "classDef class " not in flow_mmd
    assert "classDef classNode" in flow_mmd
    assert '== "serves" ==>' not in flow_mmd
    assert "==>|serves|" in flow_mmd


def test_generate_digest_markdown():
    """Verify generate_digest produces structured markdown with statistics, folders, and call interactions."""
    g = _make_sample_graph()
    digest_md = generate_digest(g)

    assert "# Architecture Digest: synthetic_app" in digest_md
    assert "## 1. System Overview" in digest_md
    assert "## 2. Directory Hierarchy" in digest_md
    assert "src/core/" in digest_md
    assert "src/api/" in digest_md
    assert "GET /status" in digest_md
    assert "Engine" in digest_md
    assert "status_handler" in digest_md
    assert "Cross-Folder Call Interactions" in digest_md


def test_generate_folder_mermaid():
    """Verify generate_folder_mermaid generates detailed nested subgraphs for a folder."""
    g = _make_sample_graph()
    folder_mmd = generate_folder_mermaid(g, folder_path="src/core")

    assert "flowchart TD" in folder_mmd
    assert 'subgraph folder_src_core ["📁 src/core"]' in folder_mmd
    assert 'subgraph file_' in folder_mmd
    assert 'subgraph class_' in folder_mmd
    assert '["run()"]:::function' in folder_mmd
    assert '["+2 internal helpers"]:::helper' in folder_mmd
    assert "classDef class " not in folder_mmd
    assert "classDef classNode" in folder_mmd


def test_cli_flow_digest_query(tmp_path: Path):
    """Test CLI commands: flow, digest, query callers-of, and query callees-of."""
    g = _make_sample_graph()
    graph_path = tmp_path / "graph.json"
    g.save(graph_path)

    # 1. cartog flow
    flow_res = runner.invoke(app, ["flow", str(graph_path), "GET /status", "--out", str(tmp_path / "out")])
    assert flow_res.exit_code == 0
    assert "Cartog Call Flow Trace" in flow_res.stdout
    assert (tmp_path / "out" / "flow_GET__status.mmd").exists()

    # 2. cartog digest
    digest_res = runner.invoke(app, ["digest", str(graph_path), "--out", str(tmp_path / "out")])
    assert digest_res.exit_code == 0
    assert "Architecture Digest" in digest_res.stdout
    assert (tmp_path / "out" / "digest.md").exists()

    # 3. cartog query callers-of
    callers_res = runner.invoke(app, ["query", "callers-of", "run", str(graph_path)])
    assert callers_res.exit_code == 0
    assert "status_handler" in callers_res.stdout

    # 4. cartog query callees-of
    callees_res = runner.invoke(app, ["query", "callees-of", "run", str(graph_path)])
    assert callees_res.exit_code == 0
    assert "_step1" in callees_res.stdout
    assert "_step2" in callees_res.stdout


def test_barrel_rewiring_exact_import_counts_per_target():
    """Verify that rewiring through a barrel file computes exact imported symbol counts per target defining file.

    Consumer imports specific symbols A1, A2 from pkg (defined in pkg/a.py) and B from pkg (defined in pkg/b.py).
    Defining file pkg/c.py defines C, which is re-exported by pkg but NOT imported by consumer.
    Assert rewired edges have exact counts: 2 for pkg/a.py, 1 for pkg/b.py, and 0 for pkg/c.py.
    """
    fa = Node.create(kind="file", name="a.py", qualified_name="pkg/a.py", path="pkg/a.py")
    fb = Node.create(kind="file", name="b.py", qualified_name="pkg/b.py", path="pkg/b.py")
    fc = Node.create(kind="file", name="c.py", qualified_name="pkg/c.py", path="pkg/c.py")
    f_barrel = Node.create(kind="file", name="__init__.py", qualified_name="pkg/__init__.py", path="pkg/__init__.py")
    f_consumer = Node.create(kind="file", name="consumer.py", qualified_name="consumer.py", path="consumer.py")

    sym_a1 = Node.create(kind="function", name="A1", qualified_name="pkg.a.A1", path="pkg/a.py", parent=fa.id)
    sym_a2 = Node.create(kind="function", name="A2", qualified_name="pkg.a.A2", path="pkg/a.py", parent=fa.id)
    sym_b = Node.create(kind="function", name="B", qualified_name="pkg.b.B", path="pkg/b.py", parent=fb.id)
    sym_c = Node.create(kind="function", name="C", qualified_name="pkg.c.C", path="pkg/c.py", parent=fc.id)

    # Barrel re-exports A1, A2 from a.py, B from b.py, C from c.py
    e_barrel_a = Edge(source=f_barrel.id, target=fa.id, kind="imports", confidence="import", count=2, attrs={"imported_names": ["A1", "A2"]})
    e_barrel_b = Edge(source=f_barrel.id, target=fb.id, kind="imports", confidence="import", count=1, attrs={"imported_names": ["B"]})
    e_barrel_c = Edge(source=f_barrel.id, target=fc.id, kind="imports", confidence="import", count=1, attrs={"imported_names": ["C"]})

    # Consumer imports A1, A2, B from pkg
    e_consumer = Edge(
        source=f_consumer.id,
        target=f_barrel.id,
        kind="imports",
        confidence="import",
        count=1,
        attrs={"imported_names": ["A1", "A2", "B"]},
    )

    graph = Graph(
        schema_version="2.0.0",
        nodes={n.id: n for n in (fa, fb, fc, f_barrel, f_consumer, sym_a1, sym_a2, sym_b, sym_c)},
        edges=[e_barrel_a, e_barrel_b, e_barrel_c, e_consumer],
        meta={"target_path": "repo"},
    )

    noise_paths = {"pkg/__init__.py"}
    rewired = rewire_view_edges(graph, noise_paths)

    consumer_imports = {e.target: e.count for e in rewired if e.kind == "imports" and e.source == f_consumer.id}

    # Exactly 2 imports from a.py (A1, A2)
    assert consumer_imports.get(fa.id) == 2
    # Exactly 1 import from b.py (B)
    assert consumer_imports.get(fb.id) == 1
    # 0 imports from c.py (C was never imported by consumer)
    assert fc.id not in consumer_imports


def test_barrel_rewiring_integration_with_build_graph():
    """Verify build_graph records imported_names and rewire_view_edges produces accurate per-target counts."""
    parsed_files = [
        ParseFileResult(
            path="pkg/a.py",
            language="python",
            hash="h1",
            symbols=[
                SymbolRecord(kind="function", name="A", qualified_name="pkg.a.A", start_line=1, start_col=0, end_line=2, end_col=10),
            ],
            imports=[],
        ),
        ParseFileResult(
            path="pkg/b.py",
            language="python",
            hash="h2",
            symbols=[
                SymbolRecord(kind="function", name="B", qualified_name="pkg.b.B", start_line=1, start_col=0, end_line=2, end_col=10),
            ],
            imports=[],
        ),
        ParseFileResult(
            path="pkg/c.py",
            language="python",
            hash="h3",
            symbols=[
                SymbolRecord(kind="function", name="C", qualified_name="pkg.c.C", start_line=1, start_col=0, end_line=2, end_col=10),
            ],
            imports=[],
        ),
        ParseFileResult(
            path="pkg/__init__.py",
            language="python",
            hash="h_init",
            symbols=[],
            imports=[
                ImportRecord(specifier="a", names=["A"], kind="relative", level=1, line=1),
                ImportRecord(specifier="b", names=["B"], kind="relative", level=1, line=2),
                ImportRecord(specifier="c", names=["C"], kind="relative", level=1, line=3),
            ],
        ),
        ParseFileResult(
            path="consumer.py",
            language="python",
            hash="h_consumer",
            symbols=[],
            imports=[
                ImportRecord(specifier="pkg", names=["A", "B"], kind="standard", level=0, line=1),
            ],
        ),
    ]

    graph = build_graph(parsed_files, target_path="test_pkg", roots=[".", "pkg"])
    noise_paths = {"pkg/__init__.py"}
    rewired = rewire_view_edges(graph, noise_paths)

    consumer_file_id = next(nid for nid, n in graph.nodes.items() if n.kind == "file" and n.path == "consumer.py")
    a_file_id = next(nid for nid, n in graph.nodes.items() if n.kind == "file" and n.path == "pkg/a.py")
    b_file_id = next(nid for nid, n in graph.nodes.items() if n.kind == "file" and n.path == "pkg/b.py")
    c_file_id = next(nid for nid, n in graph.nodes.items() if n.kind == "file" and n.path == "pkg/c.py")

    consumer_imports = {e.target: e.count for e in rewired if e.kind == "imports" and e.source == consumer_file_id}
    assert consumer_imports.get(a_file_id) == 1
    assert consumer_imports.get(b_file_id) == 1
    assert c_file_id not in consumer_imports


def test_call_counts_agree_across_map_and_digest():
    """Verify that edge labels, category summary labels, and digest report identical call counts for any given graph.

    Uses a synthetic graph with varied call weights between tests and core library functions.
    Verifies agreement across get_call_counts, generate_overview_mermaid, and generate_digest.
    """
    g = Graph(schema_version="2.0.0", meta={"target_path": "my_app"})

    # Core library file and functions
    f_core = Node.create(kind="file", name="core.py", qualified_name="src/core.py", path="src/core.py")
    fn_core1 = Node.create(kind="function", name="serve", qualified_name="src.core.serve", path="src/core.py", parent=f_core.id)
    fn_core2 = Node.create(kind="function", name="process", qualified_name="src.core.process", path="src/core.py", parent=f_core.id)

    # Test file and functions
    f_test = Node.create(kind="file", name="test_app.py", qualified_name="tests/test_app.py", path="tests/test_app.py")
    fn_test1 = Node.create(kind="function", name="test_serve", qualified_name="tests.test_app.test_serve", path="tests/test_app.py", parent=f_test.id)
    fn_test2 = Node.create(kind="function", name="test_process", qualified_name="tests.test_app.test_process", path="tests/test_app.py", parent=f_test.id)

    # Varied call edges:
    # 7 direct calls from test_serve to serve
    e_call1 = Edge(source=fn_test1.id, target=fn_core1.id, kind="calls", confidence="resolved", count=7)
    # 5 reconciled calls from test_process to process
    e_call2 = Edge(source=fn_test2.id, target=fn_core2.id, kind="calls", confidence="reconciled", count=5)
    # 3 internal calls within tests
    e_internal = Edge(source=fn_test1.id, target=fn_test2.id, kind="calls", confidence="resolved", count=3)

    g.add_node(f_core)
    g.add_node(fn_core1)
    g.add_node(fn_core2)
    g.add_node(f_test)
    g.add_node(fn_test1)
    g.add_node(fn_test2)

    g.add_edge(e_call1)
    g.add_edge(e_call2)
    g.add_edge(e_internal)

    # 1. Query shared function
    counts = get_call_counts(g)
    assert counts.total_calls == 15
    assert counts.total_reconciled == 5
    assert counts.cross_folder_calls == 12
    assert counts.by_folder_pair.get(("tests", "src")) == 12
    assert counts.reconciled_by_folder_pair.get(("tests", "src")) == 5

    # 2. Mermaid overview export
    mmd = generate_overview_mermaid(g)
    # Category summary node for tests must state "12 calls into src" and "3 internal calls"
    assert "12 calls into src" in mmd
    assert "3 internal calls" in mmd
    # Edge label must state 12 calls (5 reconciled)
    assert "12 calls (5 reconciled)" in mmd

    # 3. Digest export
    digest = generate_digest(g, include_tests=True)
    # Section 5 must list 12 calls between tests/ and src/
    assert "| `tests/` | `src/` | **12 calls** |" in digest


def test_flow_bfs_depth_limit():
    """Verify trace_call_flow respects --depth cutoff and stops traversal at external symbols."""
    g = Graph(schema_version="2.0.0", meta={"target_path": "linear_app"})

    f_src = Node.create(kind="file", name="chain.py", qualified_name="src/chain.py", path="src/chain.py")
    g.add_node(f_src)

    # Chain of calls: A -> B -> C -> D -> E
    node_a = Node.create(kind="function", name="step_a", qualified_name="src.chain.step_a", path="src/chain.py", parent=f_src.id)
    node_b = Node.create(kind="function", name="step_b", qualified_name="src.chain.step_b", path="src/chain.py", parent=f_src.id)
    node_c = Node.create(kind="function", name="step_c", qualified_name="src.chain.step_c", path="src/chain.py", parent=f_src.id)
    node_d = Node.create(kind="function", name="step_d", qualified_name="src.chain.step_d", path="src/chain.py", parent=f_src.id)
    node_e = Node.create(kind="function", name="step_e", qualified_name="src.chain.step_e", path="src/chain.py", parent=f_src.id)

    # External dependency node and hypothetical sub-call
    node_ext = Node.create(kind="dependency", name="requests", qualified_name="requests", path=None, attrs={"external": True})
    node_ext_sub = Node.create(kind="function", name="get", qualified_name="requests.get", path=None, attrs={"external": True})

    for n in (node_a, node_b, node_c, node_d, node_e, node_ext, node_ext_sub):
        g.add_node(n)

    g.add_edge(Edge(source=node_a.id, target=node_b.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=node_b.id, target=node_c.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=node_b.id, target=node_ext.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=node_ext.id, target=node_ext_sub.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=node_c.id, target=node_d.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=node_d.id, target=node_e.id, kind="calls", confidence="resolved"))

    # 1. max_depth = 2 starting at step_a:
    # Depth 0: step_a
    # Depth 1: step_b
    # Depth 2: step_c, requests (external)
    # Beyond depth 2: step_d (depth 3), step_e (depth 4)
    # Stopped at external: node_ext_sub must NOT be visited even if max_depth were larger
    visited, edges = trace_call_flow(g, starts=[node_a], max_depth=2)
    visited_names = {n.name for n in visited}

    assert "step_a" in visited_names
    assert "step_b" in visited_names
    assert "step_c" in visited_names
    assert "requests" in visited_names
    assert "step_d" not in visited_names
    assert "step_e" not in visited_names
    assert "get" not in visited_names, "Flow traversal must stop at external symbols and not expand them"

    # Traversed edges must only be up to depth 2
    edge_pairs = {(e.source, e.target) for e in edges}
    assert (node_a.id, node_b.id) in edge_pairs
    assert (node_b.id, node_c.id) in edge_pairs
    assert (node_b.id, node_ext.id) in edge_pairs
    assert (node_c.id, node_d.id) not in edge_pairs
    assert (node_ext.id, node_ext_sub.id) not in edge_pairs

    # 2. max_depth = 3 includes step_d, but still stops at external symbols
    visited_d3, edges_d3 = trace_call_flow(g, starts=[node_a], max_depth=3)
    visited_names_d3 = {n.name for n in visited_d3}
    assert "step_d" in visited_names_d3
    assert "step_e" not in visited_names_d3
    assert "get" not in visited_names_d3, "External symbol expansion must remain stopped at higher depth"


def test_flow_class_instantiation_traversal():
    """Verify flow traversal follows class instantiation into __init__ and its internal setup helpers, including class container."""
    g = Graph(schema_version="2.0.0", meta={"target_path": "service_app"})

    f_client = Node.create(kind="file", name="client.py", qualified_name="src/client.py", path="src/client.py")
    f_service = Node.create(kind="file", name="service.py", qualified_name="src/service.py", path="src/service.py")
    g.add_node(f_client)
    g.add_node(f_service)

    # Caller function
    fn_client = Node.create(
        kind="function",
        name="create_app",
        qualified_name="src.client.create_app",
        path="src/client.py",
        parent=f_client.id,
        range=SourceRange(5, 0, 10, 0),
    )
    g.add_node(fn_client)

    # Class AppService
    cls_service = Node.create(
        kind="class",
        name="AppService",
        qualified_name="src/service.py:AppService",
        path="src/service.py",
        parent=f_service.id,
        range=SourceRange(1, 0, 40, 0),
    )
    g.add_node(cls_service)

    # __init__ method
    meth_init = Node.create(
        kind="method",
        name="__init__",
        qualified_name="src.service.AppService.__init__",
        path="src/service.py",
        parent=cls_service.id,
        range=SourceRange(2, 4, 15, 0),
    )
    # Internal helpers called by __init__
    meth_cfg = Node.create(
        kind="method",
        name="_configure_routes",
        qualified_name="src.service.AppService._configure_routes",
        path="src/service.py",
        parent=cls_service.id,
        range=SourceRange(16, 4, 25, 0),
    )
    meth_db = Node.create(
        kind="method",
        name="_connect_db",
        qualified_name="src.service.AppService._connect_db",
        path="src/service.py",
        parent=cls_service.id,
        range=SourceRange(26, 4, 35, 0),
    )
    g.add_node(meth_init)
    g.add_node(meth_cfg)
    g.add_node(meth_db)

    # Class instantiation edge: create_app() -> AppService.__init__()
    # Decision: Class instantiation connects directly to __init__ when explicitly resolved
    g.add_edge(Edge(source=fn_client.id, target=meth_init.id, kind="calls", confidence="resolved"))
    # __init__ calls helpers
    g.add_edge(Edge(source=meth_init.id, target=meth_cfg.id, kind="calls", confidence="resolved"))
    g.add_edge(Edge(source=meth_cfg.id, target=meth_db.id, kind="calls", confidence="resolved"))

    visited, edges = trace_call_flow(g, starts=[fn_client], max_depth=3)
    visited_names = {n.name for n in visited}

    assert "create_app" in visited_names
    assert "__init__" in visited_names
    assert "_configure_routes" in visited_names
    assert "_connect_db" in visited_names
    assert "AppService" in visited_names, "Enclosing class container must be included when class methods are traversed"

    # Mermaid export must wrap methods in the 🏛️ AppService subgraph
    flow_mmd = generate_flow_mermaid(visited, edges, target_name="create_app")
    assert 'subgraph class_' in flow_mmd
    assert '🏛️ AppService' in flow_mmd
    assert 'flow_' in flow_mmd

    # 2. Also verify class node target: when caller calls class node directly (AST invocation style),
    # trace_call_flow automatically discovers and traverses its __init__ constructor and helpers
    g2 = Graph(schema_version="2.0.0", meta={"target_path": "service_app2"})
    for n in (f_client, f_service, fn_client, cls_service, meth_init, meth_cfg, meth_db):
        g2.add_node(n)
    # Caller calls class directly: create_app() -> AppService
    g2.add_edge(Edge(source=fn_client.id, target=cls_service.id, kind="calls", confidence="heuristic"))
    g2.add_edge(Edge(source=meth_init.id, target=meth_cfg.id, kind="calls", confidence="resolved"))
    g2.add_edge(Edge(source=meth_cfg.id, target=meth_db.id, kind="calls", confidence="resolved"))

    visited2, edges2 = trace_call_flow(g2, starts=[fn_client], max_depth=3)
    visited_names2 = {n.name for n in visited2}
    assert "create_app" in visited_names2
    assert "AppService" in visited_names2
    assert "__init__" in visited_names2
    assert "_configure_routes" in visited_names2
    assert "_connect_db" in visited_names2


def test_flow_overrides_edge_styling():
    """Verify trace_call_flow traverses 'overrides' edges and export_mermaid renders them with dashed syntax."""
    g = Graph(schema_version="2.0.0", meta={"target_path": "override_app"})

    f_base = Node.create(kind="file", name="base.py", qualified_name="src/base.py", path="src/base.py")
    f_custom = Node.create(kind="file", name="custom.py", qualified_name="src/custom.py", path="src/custom.py")
    g.add_node(f_base)
    g.add_node(f_custom)

    cls_base = Node.create(kind="class", name="BaseHandler", qualified_name="src/base.py:BaseHandler", path="src/base.py", parent=f_base.id)
    cls_custom = Node.create(kind="class", name="CustomHandler", qualified_name="src/custom.py:CustomHandler", path="src/custom.py", parent=f_custom.id)
    g.add_node(cls_base)
    g.add_node(cls_custom)

    meth_base = Node.create(kind="method", name="handle", qualified_name="src.base.BaseHandler.handle", path="src/base.py", parent=cls_base.id)
    meth_custom = Node.create(kind="method", name="handle", qualified_name="src.custom.CustomHandler.handle", path="src/custom.py", parent=cls_custom.id)
    g.add_node(meth_base)
    g.add_node(meth_custom)

    route_node = Node.create(
        kind="route",
        name="GET /custom",
        qualified_name="src/custom.py:GET /custom",
        path="src/custom.py",
        parent=f_custom.id,
        attrs={"handler": "handle"},
    )
    g.add_node(route_node)

    # Route serves CustomHandler.handle
    g.add_edge(Edge(source=route_node.id, target=meth_custom.id, kind="serves", confidence="resolved"))
    # CustomHandler.handle overrides BaseHandler.handle
    g.add_edge(Edge(source=meth_custom.id, target=meth_base.id, kind="overrides", confidence="resolved"))

    # BFS trace from route follows serves and overrides
    visited, edges = trace_call_flow(g, starts=[route_node], max_depth=2)
    visited_names = {n.name for n in visited}
    assert "GET /custom" in visited_names
    assert meth_custom.name in visited_names
    assert meth_base.name in visited_names

    overrides_edges = [e for e in edges if e.kind == "overrides"]
    assert len(overrides_edges) == 1
    assert overrides_edges[0].source == meth_custom.id
    assert overrides_edges[0].target == meth_base.id

    # Mermaid export must format the overrides edge with dashed line -.->|overrides|
    flow_mmd = generate_flow_mermaid(visited, edges, target_name="GET /custom")
    assert "-.->|overrides|" in flow_mmd
    assert "-->|overrides|" not in flow_mmd
    assert "==>|overrides|" not in flow_mmd


def test_map_function_level_boundary_symbols_and_helpers():
    """Verify function-level map displays boundary functions/routes/commands and groups internal helpers."""
    g = _make_sample_graph()
    mmd = generate_overview_mermaid(g, level="function")

    # Boundary symbols must be drawn
    assert "GET /status" in mmd
    assert "status_handler" in mmd
    assert "run" in mmd

    # Internal helpers must be collapsed into +N helpers
    assert "+2 helpers" in mmd or "+2 internal helpers" in mmd
    assert "+1 helpers" in mmd or "+1 internal helpers" in mmd
    assert "_step1" not in mmd, "Internal helper _step1 must not be drawn as individual node"
    assert "_step2" not in mmd, "Internal helper _step2 must not be drawn as individual node"


def test_map_node_budget_fallback_to_file_level():
    """Verify function-level map falls back to file level when node budget is exceeded."""
    g = _make_sample_graph()
    # At function level, sample graph has ~10 nodes. Setting max_nodes=4 forces fallback.
    mmd = generate_overview_mermaid(g, level="function", max_nodes=4)

    # Must fall back to file-level nodes (files inside folders, no individual functions)
    assert "engine.py" in mmd
    assert "routes.py" in mmd
    assert "status_handler" not in mmd, "Function nodes must not appear after file-level fallback"
    assert "GET /status" not in mmd


def test_map_edge_rollup_to_containers():
    """Verify call edges to hidden/collapsed helper functions roll up to the parent container."""
    g = Graph(schema_version="2.0.0", meta={"target_path": "rollup_app"})

    f_api = Node.create(kind="file", name="api.py", qualified_name="src/api.py", path="src/api.py")
    f_svc = Node.create(kind="file", name="svc.py", qualified_name="src/svc.py", path="src/svc.py")
    g.add_node(f_api)
    g.add_node(f_svc)

    fn_api = Node.create(
        kind="function", name="external_trigger", qualified_name="api.external_trigger",
        path="src/api.py", parent=f_api.id, range=SourceRange(1, 0, 4, 0),
    )
    fn_caller = Node.create(
        kind="function", name="call_internal", qualified_name="svc.call_internal",
        path="src/svc.py", parent=f_svc.id, range=SourceRange(5, 0, 10, 0),
    )
    cls_svc = Node.create(
        kind="class", name="BackendService", qualified_name="svc.BackendService",
        path="src/svc.py", parent=f_svc.id, range=SourceRange(1, 0, 40, 0),
    )
    # meth_helper is an internal helper in BackendService
    meth_helper = Node.create(
        kind="method", name="_init_db", qualified_name="svc.BackendService._init_db",
        path="src/svc.py", parent=cls_svc.id, range=SourceRange(2, 4, 15, 0),
    )
    g.add_node(fn_api)
    g.add_node(fn_caller)
    g.add_node(cls_svc)
    g.add_node(meth_helper)

    # Cross-file call makes call_internal a boundary function
    g.add_edge(Edge(source=fn_api.id, target=fn_caller.id, kind="calls", confidence="resolved", count=1))
    # Edge from boundary function to internal helper
    g.add_edge(Edge(source=fn_caller.id, target=meth_helper.id, kind="calls", confidence="resolved", count=4))

    mmd = generate_overview_mermaid(g, level="function")

    # The caller is a boundary function; the helper is rolled up to class BackendService container
    assert "call_internal" in mmd
    assert "BackendService" in mmd
    # Edge should roll up to BackendService class container with count 4
    assert "4 calls" in mmd


def test_map_unique_container_membership():
    """Verify each file appears in exactly one folder, and no duplicate container nodes exist."""
    g = _make_sample_graph()
    mmd = generate_overview_mermaid(g, level="function")

    # Count occurrences of file subgraphs
    assert mmd.count('subgraph file_') == 2
    assert mmd.count('subgraph class_') == 1
    # Check matching subgraph / end counts
    subgraph_count = mmd.count('subgraph ')
    end_count = mmd.count('end')
    assert subgraph_count <= end_count


def test_map_method_label_format():
    """Verify methods are labeled 'Class.method() :line' and functions 'func() :line'."""
    g = _make_sample_graph()
    mmd = generate_overview_mermaid(g, level="function")

    # Engine.run method with line 2
    assert "Engine.run() :2" in mmd
    # status_handler function with line 5
    assert "status_handler() :5" in mmd


def test_digest_ranks_files_by_connectivity():
    """Verify generate_digest ranks files within folders by cross-file connectivity descending."""
    g = Graph(schema_version="2.0.0", meta={"target_path": "rank_app"})

    # Two files in src/: a_isolated.py (0 connections) and z_connected.py (10 connections)
    f_isolated = Node.create(kind="file", name="a_isolated.py", qualified_name="src/a_isolated.py", path="src/a_isolated.py")
    f_connected = Node.create(kind="file", name="z_connected.py", qualified_name="src/z_connected.py", path="src/z_connected.py")
    f_other = Node.create(kind="file", name="other.py", qualified_name="pkg/other.py", path="pkg/other.py")

    g.add_node(f_isolated)
    g.add_node(f_connected)
    g.add_node(f_other)

    # Add cross-file calls connecting z_connected to other.py
    g.add_edge(Edge(source=f_other.id, target=f_connected.id, kind="calls", confidence="resolved", count=10))

    digest = generate_digest(g)

    # In src/, z_connected.py must appear BEFORE a_isolated.py
    pos_connected = digest.find("`z_connected.py`")
    pos_isolated = digest.find("`a_isolated.py`")
    assert pos_connected != -1
    assert pos_isolated != -1
    assert pos_connected < pos_isolated, f"Expected z_connected.py before a_isolated.py in digest, got pos_connected={pos_connected}, pos_isolated={pos_isolated}"


def test_digest_attributes_constructor_to_class():
    """Verify Section 4 attributes __init__ constructor activity to the parent class and does not output bare __init__ rows."""
    g = Graph(schema_version="2.0.0", meta={"target_path": "ctor_app"})

    f_server = Node.create(kind="file", name="server.py", qualified_name="src/server.py", path="src/server.py")
    f_client = Node.create(kind="file", name="client.py", qualified_name="src/client.py", path="src/client.py")
    g.add_node(f_server)
    g.add_node(f_client)

    cls_server = Node.create(
        kind="class", name="Server", qualified_name="src.server.Server",
        path="src/server.py", parent=f_server.id, range=SourceRange(1, 0, 50, 0),
    )
    meth_init = Node.create(
        kind="method", name="__init__", qualified_name="src.server.Server.__init__",
        path="src/server.py", parent=cls_server.id, range=SourceRange(2, 4, 10, 0),
    )
    fn_client = Node.create(
        kind="function", name="boot", qualified_name="src.client.boot",
        path="src/client.py", parent=f_client.id, range=SourceRange(1, 0, 10, 0),
    )

    g.add_node(cls_server)
    g.add_node(meth_init)
    g.add_node(fn_client)

    # Cross-file constructor call from boot to Server.__init__
    g.add_edge(Edge(source=fn_client.id, target=meth_init.id, kind="calls", confidence="resolved", count=5))

    digest = generate_digest(g)

    # Section 4 must attribute the 5 connections to class Server
    assert "## 4. Key Boundary Symbols" in digest
    assert "**`Server`**" in digest
    assert "5 connections" in digest
    # Bare __init__ row must NOT appear in Section 4
    section_4 = digest.split("## 4. Key Boundary Symbols")[1].split("## 5.")[0]
    assert "**`__init__`**" not in section_4
    assert "`method`" not in section_4 or "**`__init__`**" not in section_4





