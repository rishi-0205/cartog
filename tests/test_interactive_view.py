"""Tests for Milestone 11: Interactive Cytoscape Viewer (cartog view)."""

import json
import re
import tomllib
from pathlib import Path

from typer.testing import CliRunner

import cartog
from cartog.cli import app
from cartog.model import Edge, Graph, Node, SourceRange

runner = CliRunner()


def test_view_assets_packaged_and_loadable():
    """Verify that all required offline Cytoscape assets exist, are non-empty, and are declared in pyproject.toml."""
    cartog_pkg_dir = Path(cartog.__file__).parent
    assets_dir = cartog_pkg_dir / "render" / "assets"
    
    assert assets_dir.is_dir(), f"render/assets directory not found at {assets_dir}"
    
    required_assets = [
        "cytoscape.min.js",
        "cytoscape-expand-collapse.js",
        "cytoscape-fcose.js",
        "layout-base.js",
        "cose-base.js",
        "viewer.css",
        "viewer.js",
        "VENDOR_LICENSES.txt",
    ]
    
    for asset_name in required_assets:
        asset_file = assets_dir / asset_name
        assert asset_file.is_file(), f"Required asset '{asset_name}' missing from {assets_dir}"
        content = asset_file.read_text(encoding="utf-8")
        assert len(content.strip()) > 50, f"Asset '{asset_name}' is unexpectedly small or empty"

    # Verify pyproject.toml includes render/assets/* in package-data
    repo_root = cartog_pkg_dir.parent
    pyproject_file = repo_root / "pyproject.toml"
    assert pyproject_file.is_file()
    
    with open(pyproject_file, "rb") as f:
        pyproject_data = tomllib.load(f)
    
    pkg_data = pyproject_data.get("tool", {}).get("setuptools", {}).get("package-data", {}).get("cartog", [])
    assert any("render/assets" in p for p in pkg_data), f"pyproject.toml package-data for cartog must include render/assets/*, found: {pkg_data}"





def _build_test_graph() -> Graph:
    """Construct a synthetic graph with folder, file, class, function, and edge relations."""
    g = Graph()
    g.meta = {"target_path": "my_project", "cartog_version": "0.1.0"}

    # Folders
    folder = Node(id="folder_src", name="src", qualified_name="src", kind="folder", path="src")
    g.add_node(folder)

    # Files
    f1 = Node(id="file_app", name="app.py", qualified_name="src/app.py", kind="file", path="src/app.py", range=SourceRange(1, 0, 50, 0))
    f2 = Node(id="file_core", name="core.py", qualified_name="src/core.py", kind="file", path="src/core.py", range=SourceRange(1, 0, 100, 0))
    g.add_node(f1)
    g.add_node(f2)

    # Classes & Functions
    cls_cli = Node(id="cls_cli", name="CLI", qualified_name="src/core.py:CLI", kind="class", path="src/core.py", range=SourceRange(10, 0, 20, 0), parent="file_core")
    fn_main = Node(id="fn_main", name="main", qualified_name="src/app.py:main", kind="function", path="src/app.py", range=SourceRange(5, 0, 8, 0), parent="file_app")
    fn_run = Node(id="fn_run", name="run", qualified_name="src/core.py:run", kind="function", path="src/core.py", range=SourceRange(25, 0, 30, 0), parent="file_core")
    g.add_node(cls_cli)
    g.add_node(fn_main)
    g.add_node(fn_run)

    # Structural contains edges
    g.add_edge(Edge(source="folder_src", target="file_app", kind="contains", confidence="resolved"))
    g.add_edge(Edge(source="folder_src", target="file_core", kind="contains", confidence="resolved"))
    g.add_edge(Edge(source="file_core", target="cls_cli", kind="contains", confidence="resolved"))
    g.add_edge(Edge(source="file_app", target="fn_main", kind="contains", confidence="resolved"))
    g.add_edge(Edge(source="file_core", target="fn_run", kind="contains", confidence="resolved"))

    # Cross-file semantic edges
    g.add_edge(Edge(source="fn_main", target="fn_run", kind="calls", confidence="resolved", count=3))
    g.add_edge(Edge(source="file_app", target="file_core", kind="imports", confidence="import", count=1))

    return g


def test_export_html_generates_valid_offline_file(tmp_path: Path):
    """Verify that generate_html_map creates a complete offline map.html with valid embedded data."""
    from cartog.export_html import generate_html_map

    graph = _build_test_graph()
    out_file = tmp_path / "map.html"

    html_content = generate_html_map(graph, out_file=out_file)
    assert out_file.is_file(), "map.html was not written to disk"
    assert len(html_content) > 1000

    # Extract CARTOG_VIEW_DATA JSON payload
    match = re.search(r'window\.CARTOG_VIEW_DATA\s*=\s*(\{.*?\});\s*</script>', html_content, re.DOTALL)
    assert match is not None, "CARTOG_VIEW_DATA JSON payload not found in map.html"

    data = json.loads(match.group(1))
    assert "elements" in data
    assert "meta" in data

    elements = data["elements"]
    nodes = [el["data"] for el in elements if "source" not in el["data"]]
    edges = [el["data"] for el in elements if "source" in el["data"]]

    assert len(nodes) >= 3
    assert len(edges) >= 1

    # Verify compound hierarchy (some nodes must have a parent property)
    nodes_with_parents = [n for n in nodes if "parent" in n]
    assert len(nodes_with_parents) > 0, "Expected compound nodes with 'parent' attributes"


def test_export_html_no_external_network_tags(tmp_path: Path):
    """Verify that map.html is 100% self-contained with ZERO external network references."""
    from cartog.export_html import generate_html_map

    graph = _build_test_graph()
    out_file = tmp_path / "map.html"

    html_content = generate_html_map(graph, out_file=out_file)

    # Check for external script src or link href
    external_scripts = re.findall(r'<script[^>]+src=["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE)
    external_links = re.findall(r'<link[^>]+href=["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE)

    assert not external_scripts, f"Found external script dependencies: {external_scripts}"
    assert not external_links, f"Found external stylesheet dependencies: {external_links}"




def test_cli_view_command_default(tmp_path: Path):
    """Verify 'cartog view <path> --out <out_dir> --no-open' produces map.html in overview mode."""
    graph = _build_test_graph()
    graph_path = tmp_path / "graph.json"
    graph.save(graph_path)

    out_dir = tmp_path / "view_out"
    res = runner.invoke(app, ["view", str(graph_path), "--out", str(out_dir), "--no-open"])
    assert res.exit_code == 0, res.stdout
    assert "Interactive map written to" in res.stdout

    map_html = out_dir / "map.html"
    assert map_html.is_file()
    content = map_html.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "CARTOG_VIEW_DATA" in content
    assert "Interactive Codebase Architecture" in content


def test_cli_view_command_flow_mode(tmp_path: Path):
    """Verify 'cartog view <path> --flow <symbol> --no-open' produces map.html in flow mode."""
    graph = _build_test_graph()
    graph_path = tmp_path / "graph.json"
    graph.save(graph_path)

    out_dir = tmp_path / "view_flow_out"
    res = runner.invoke(app, ["view", str(graph_path), "--flow", "main", "--out", str(out_dir), "--no-open"])
    assert res.exit_code == 0, res.stdout
    assert "Interactive map written to" in res.stdout

    map_html = out_dir / "map.html"
    assert map_html.is_file()
    content = map_html.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Call Flow Trace" in content


def test_convert_view_tree_edge_rollup():
    """Verify that multiple edges between the same (source, target, kind) are rolled up into one edge with aggregated counts and labels."""
    from cartog.export_html import convert_view_tree_to_cytoscape_elements
    from cartog.views import build_universal_view_tree

    g = Graph()
    g.meta = {"target_path": "rollup_project"}
    n1 = Node(id="fn_a", name="fn_a", qualified_name="a:fn_a", kind="function", path="a.py")
    n2 = Node(id="fn_b", name="fn_b", qualified_name="b:fn_b", kind="function", path="b.py")
    g.add_node(n1)
    g.add_node(n2)

    # 3 separate calls from fn_a to fn_b
    g.add_edge(Edge(source="fn_a", target="fn_b", kind="calls", confidence="resolved", count=2))
    g.add_edge(Edge(source="fn_a", target="fn_b", kind="calls", confidence="resolved", count=3))
    # 1 reference edge from fn_a to fn_b
    g.add_edge(Edge(source="fn_a", target="fn_b", kind="references", confidence="resolved", count=1))

    tree = build_universal_view_tree(g)
    elements = convert_view_tree_to_cytoscape_elements(tree, g)

    edges = [el["data"] for el in elements if "source" in el["data"]]
    # Should be exactly 2 rolled-up edges (1 calls, 1 references) instead of 3
    assert len(edges) == 2, f"Expected 2 rolled-up edges, found {len(edges)}: {edges}"

    calls_edge = next(e for e in edges if e["kind"] == "calls")
    assert calls_edge["count"] == 5, f"Expected aggregated count 5, got {calls_edge['count']}"
    assert calls_edge["label"] == "5 calls", f"Expected label '5 calls', got {calls_edge['label']}"
    assert calls_edge.get("is_reference") is False

    ref_edge = next(e for e in edges if e["kind"] == "references")
    assert ref_edge["count"] == 1
    assert ref_edge.get("is_reference") is True


def test_export_html_includes_routing_and_filter_controls(tmp_path: Path):
    """Verify that map.html includes orthogonal routing, layout selector, and references toggle controls."""
    from cartog.export_html import generate_html_map

    graph = _build_test_graph()
    out_file = tmp_path / "map.html"
    html_content = generate_html_map(graph, out_file=out_file)

    # Controls must exist in the header
    assert 'id="select-layout"' in html_content
    assert 'id="select-routing"' in html_content
    assert 'id="btn-toggle-references"' in html_content

    # Cytoscape stylesheet must default to 'taxi' orthogonal curve style
    assert "'curve-style': 'taxi'" in html_content or '"curve-style": "taxi"' in html_content


def test_universal_view_tree_expand_internal_helpers():
    """Verify that build_universal_view_tree with include_helpers=True retains individual helper symbols and their edges."""
    from cartog.export_html import convert_view_tree_to_cytoscape_elements
    from cartog.views import build_universal_view_tree

    g = Graph()
    g.meta = {"target_path": "helper_test"}

    # File 1 with a boundary function and an internal helper
    f1 = Node(id="file_core", name="core.py", qualified_name="core.py", kind="file", path="core.py")
    fn_main = Node(id="fn_main", name="main", qualified_name="core:main", kind="function", path="core.py", parent="file_core")
    fn_helper = Node(id="fn_helper", name="_clean", qualified_name="core:_clean", kind="function", path="core.py", parent="file_core")

    # File 2 with a target function
    f2 = Node(id="file_util", name="util.py", qualified_name="util.py", kind="file", path="util.py")
    fn_util = Node(id="fn_util", name="format", qualified_name="util:format", kind="function", path="util.py", parent="file_util")

    g.add_node(f1)
    g.add_node(fn_main)
    g.add_node(fn_helper)
    g.add_node(f2)
    g.add_node(fn_util)

    # fn_main calls external fn_util (boundary call) and calls internal helper fn_helper
    g.add_edge(Edge(source="fn_main", target="fn_util", kind="calls", confidence="resolved", count=1))
    g.add_edge(Edge(source="fn_main", target="fn_helper", kind="calls", confidence="resolved", count=2))

    # 1. Default (include_helpers=False) should collapse fn_helper into a composite helper_group
    tree_collapsed = build_universal_view_tree(g, include_helpers=False)
    core_children_collapsed = [c for c in tree_collapsed.children[0].children[0].children]
    kinds_collapsed = {c.kind for c in core_children_collapsed}
    assert "helper_group" in kinds_collapsed

    # 2. include_helpers=True should retain fn_helper as an individual function node
    tree_expanded = build_universal_view_tree(g, include_helpers=True)
    core_children_expanded = [c for c in tree_expanded.children[0].children[0].children]
    expanded_ids = {c.id for c in core_children_expanded}
    assert "fn_helper" in expanded_ids
    assert "helper_group" not in {c.kind for c in core_children_expanded}

    helper_vn = next(c for c in core_children_expanded if c.id == "fn_helper")
    assert helper_vn.attrs.get("is_helper") is True

    # 3. Cytoscape elements should contain the internal call edge between fn_main and fn_helper
    elements = convert_view_tree_to_cytoscape_elements(tree_expanded, g)
    edges = [el["data"] for el in elements if "source" in el["data"]]
    internal_edge = next((e for e in edges if e["source"] == "fn_main" and e["target"] == "fn_helper"), None)
    assert internal_edge is not None, f"Expected internal call edge to helper, found: {edges}"
    assert internal_edge["count"] == 2


def test_viewer_expanded_spacing_and_helper_toggle(tmp_path: Path):
    """Verify that map.html includes generous compound padding (>=30px), helper toggle, and spacious layout physics."""
    from cartog.export_html import generate_html_map

    graph = _build_test_graph()
    out_file = tmp_path / "map.html"
    html_content = generate_html_map(graph, out_file=out_file)

    # 1. Helper toggle button in header
    assert 'id="btn-toggle-helpers"' in html_content

    # 2. Generous compound parent padding (>=30px) in stylesheet
    assert "'padding': '35px'" in html_content or '"padding": "35px"' in html_content or "'padding': '36px'" in html_content

    # 3. Expanded layout physics with large idealEdgeLength (>=200) and nodeRepulsion (>=60000)
    assert "idealEdgeLength: 240" in html_content or "idealEdgeLength: 220" in html_content
    assert "nodeRepulsion: 85000" in html_content or "nodeRepulsion: 75000" in html_content or "nodeRepulsion: 65000" in html_content





def test_export_html_raw_graph_fallback_reads_range():
    """F4: the raw-graph fallback must read ``SourceRange.start_line``, not ``range[0]``."""
    from cartog.export_html import convert_view_tree_to_cytoscape_elements
    from cartog.model import Graph, Node, SourceRange
    from cartog.views import build_universal_view_tree

    graph = Graph(meta={"target_path": "fallback"})
    graph.add_node(
        Node(
            id="fn_orphan",
            name="orphan",
            qualified_name="orphan.py:orphan",
            kind="function",
            path="orphan.py",
            range=SourceRange(7, 0, 9, 0),
        )
    )

    tree = build_universal_view_tree(graph)
    assert tree.children == [], "fixture must exercise the raw-graph fallback"

    elements = convert_view_tree_to_cytoscape_elements(tree, graph)
    nodes = [e["data"] for e in elements if "source" not in e["data"]]
    assert [n["id"] for n in nodes] == ["fn_orphan"]
    assert nodes[0]["line"] == 7


def test_export_html_raw_graph_fallback_parent():
    """F4: the raw-graph fallback must read ``node.parent``, not ``attrs["parent"]``."""
    from cartog.export_html import convert_view_tree_to_cytoscape_elements
    from cartog.model import Graph, Node, SourceRange
    from cartog.views import build_universal_view_tree

    graph = Graph(meta={"target_path": "fallback"})
    graph.add_node(
        Node(
            id="fn_parent",
            name="parent",
            qualified_name="p.py:parent",
            kind="function",
            path="p.py",
            range=SourceRange(1, 0, 2, 0),
        )
    )
    graph.add_node(
        Node(
            id="fn_child",
            name="child",
            qualified_name="p.py:child",
            kind="function",
            path="p.py",
            range=SourceRange(4, 0, 5, 0),
            parent="fn_parent",
        )
    )

    tree = build_universal_view_tree(graph)
    assert tree.children == [], "fixture must exercise the raw-graph fallback"

    elements = convert_view_tree_to_cytoscape_elements(tree, graph)
    by_id = {e["data"]["id"]: e["data"] for e in elements if "source" not in e["data"]}
    assert by_id["fn_child"]["parent"] == "fn_parent"


def _hidden_helper_graph():
    """F3 fixture: a route calls a collapsed helper and a visible boundary function."""
    from cartog.model import Edge, Graph, Node

    g = Graph(meta={"target_path": "rollup"})
    f_core = Node(id="file_core", name="core.py", qualified_name="core.py", kind="file", path="core.py")
    f_util = Node(id="file_util", name="util.py", qualified_name="util.py", kind="file", path="util.py")
    route = Node(
        id="fn_index", name="index", qualified_name="core:index", kind="route",
        path="core.py", parent="file_core",
    )
    helper = Node(
        id="fn_internal", name="_internal", qualified_name="core:_internal", kind="function",
        path="core.py", parent="file_core",
    )
    target = Node(
        id="fn_format", name="format", qualified_name="util:format", kind="function",
        path="util.py", parent="file_util",
    )
    for node in (f_core, f_util, route, helper, target):
        g.add_node(node)
    g.add_edge(Edge(source="fn_index", target="fn_internal", kind="calls", confidence="resolved", count=1))
    g.add_edge(Edge(source="fn_index", target="fn_format", kind="calls", confidence="resolved", count=1))
    return g


def test_hidden_endpoint_rolls_up_to_visible_ancestor():
    """F3: an edge to a collapsed helper must roll up to its nearest visible ancestor."""
    from cartog.export_html import convert_view_tree_to_cytoscape_elements
    from cartog.views import build_universal_view_tree

    graph = _hidden_helper_graph()
    tree = build_universal_view_tree(graph, include_helpers=False)
    elements = convert_view_tree_to_cytoscape_elements(tree, graph)

    node_ids = {e["data"]["id"] for e in elements if "source" not in e["data"]}
    assert "fn_internal" not in node_ids, "fixture must collapse the helper"
    assert "file_core" in node_ids

    edge_keys = {
        (e["data"]["source"], e["data"]["target"], e["data"]["kind"])
        for e in elements
        if "source" in e["data"]
    }
    assert ("fn_index", "file_core", "calls") in edge_keys, edge_keys
    assert ("fn_index", "fn_format", "calls") in edge_keys, edge_keys


def test_rollup_counts_sum_to_underlying_edges():
    """Rolled-up weights plus dropped self-edges must equal the underlying edge weights."""
    from cartog.export_html import convert_view_tree_to_cytoscape_elements
    from cartog.model import Edge, Node
    from cartog.views import build_universal_view_tree

    graph = _hidden_helper_graph()
    graph.add_node(
        Node(id="fn_other", name="other", qualified_name="core:other", kind="function",
             path="core.py", parent="file_core")
    )
    graph.add_node(
        Node(id="fn_util_worker", name="worker", qualified_name="util:worker", kind="function",
             path="util.py", parent="file_util")
    )
    # Both endpoints hidden: rolls up to file_core -> file_core, a self-edge to drop.
    graph.add_edge(Edge(source="fn_other", target="fn_internal", kind="calls", confidence="resolved", count=1))
    # Only the source is hidden: rolls up to the visible file container.
    graph.add_edge(Edge(source="fn_util_worker", target="fn_format", kind="calls", confidence="resolved", count=1))

    tree = build_universal_view_tree(graph, include_helpers=False)
    stats: dict[str, int] = {}
    elements = convert_view_tree_to_cytoscape_elements(tree, graph, stats=stats)

    edges = [e["data"] for e in elements if "source" in e["data"]]
    underlying = sum(e.count for e in graph.edges if e.kind != "contains")
    emitted = sum(e["count"] for e in edges)

    assert stats["underlying_edges"] == underlying == 4
    assert stats["rolled_up_edges"] == 3
    assert stats["dropped_self_edges"] == 1
    assert emitted + stats["dropped_self_edges"] == underlying, (emitted, stats)
    assert stats["emitted_edges"] == len(edges)


def test_mermaid_function_level_rollup_matches_viewer():
    """F3: the function-level Mermaid exporter rolls hidden helpers up the same way as the viewer."""
    from cartog.export_html import convert_view_tree_to_cytoscape_elements
    from cartog.export_mermaid import generate_overview_mermaid
    from cartog.views import build_universal_view_tree

    graph = _hidden_helper_graph()
    tree = build_universal_view_tree(graph, include_helpers=False)
    elements = convert_view_tree_to_cytoscape_elements(tree, graph)
    edge_keys = {
        (e["data"]["source"], e["data"]["target"], e["data"]["kind"])
        for e in elements
        if "source" in e["data"]
    }
    assert ("fn_index", "file_core", "calls") in edge_keys, edge_keys

    mmd = generate_overview_mermaid(graph, level="function")
    assert "fn_fn_index -->|1 call| file_file_core" in mmd, mmd
    assert "fn_fn_index -->|1 call| fn_fn_format" in mmd, mmd


def test_html_payload_reports_rolled_up_edges(tmp_path):
    """The viewer payload and header note must surface the rolled-up edge count."""
    from cartog.export_html import generate_html_map

    graph = _hidden_helper_graph()
    stats: dict[str, int] = {}
    html = generate_html_map(
        graph,
        out_file=tmp_path / "map.html",
        include_helpers=False,
        stats=stats,
    )

    assert stats["rolled_up_edges"] == 1
    assert stats["emitted_edges"] == 2
    assert '"rolled_up_edges":1' in html
    assert 'id="rollup-note"' in html
    assert "1 edge rolled up to a visible ancestor" in html
