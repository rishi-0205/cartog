"""Interactive Cytoscape.js HTML Export Engine for Cartog.

Generates a 100% self-contained, offline HTML map (map.html) with
dynamic compound expand/collapse, sidebar details, and vscode:// editor links.
"""

import json
from pathlib import Path
from typing import Any, Optional

from cartog.model import Graph, Node, Edge
from cartog.views import build_universal_view_tree, ViewNode, trace_call_flow


def _load_asset(name: str) -> str:
    """Load text content of a bundled asset from cartog/view_assets/."""
    assets_dir = Path(__file__).parent / "view_assets"
    asset_path = assets_dir / name
    if not asset_path.is_file():
        raise FileNotFoundError(f"Required viewer asset not found: {asset_path}")
    return asset_path.read_text(encoding="utf-8")


def convert_view_tree_to_cytoscape_elements(
    tree: ViewNode,
    graph: Graph,
    flow_nodes: Optional[list[Node]] = None,
    flow_edges: Optional[list[Edge]] = None,
) -> list[dict[str, Any]]:
    """Convert Universal View Model hierarchy and semantic edges into Cytoscape element definitions."""
    elements: list[dict[str, Any]] = []
    registered_node_ids: set[str] = set()

    # If in flow mode, restrict visible nodes/edges to the flow trace
    flow_node_ids = {n.id for n in flow_nodes} if flow_nodes else None
    flow_edge_pairs = {(e.source, e.target) for e in flow_edges} if flow_edges else None

    def _traverse(node: ViewNode, parent_id: Optional[str] = None):
        # In flow mode, if none of the descendants are in flow, skip
        if flow_node_ids is not None:
            descendant_ids = _collect_ids(node)
            if not descendant_ids.intersection(flow_node_ids):
                return

        node_data: dict[str, Any] = {
            "id": node.id,
            "label": node.name,
            "kind": node.kind,
            "path": node.path or "",
            "line": node.attrs.get("line", 1),
            "qualified_name": node.attrs.get("qualified_name", node.name),
            "description": node.attrs.get("description", ""),
            "is_helper": 1 if node.attrs.get("is_helper") else 0,
        }

        # Root subsystem / top-level container has no parent
        if parent_id and parent_id != "root":
            node_data["parent"] = parent_id

        # Skip adding dummy root to the visual elements if multiple top-level folders exist
        if node.id != "root":
            elements.append({"data": node_data})
            registered_node_ids.add(node.id)

        next_parent = node.id if node.id != "root" else None
        for child in node.children:
            _traverse(child, parent_id=next_parent)

    def _collect_ids(vn: ViewNode) -> set[str]:
        s = {vn.id}
        for c in vn.children:
            s.update(_collect_ids(c))
        return s

    _traverse(tree)

    # If the synthetic tree didn't register nodes (e.g. raw graph fallback), register nodes directly
    if not registered_node_ids:
        for nid, node in sorted(graph.nodes.items()):
            if node.kind in ("dependency", "ci_job"):
                continue
            parent = node.parent
            data = {
                "id": node.id,
                "label": node.name,
                "kind": node.kind,
                "path": node.path or "",
                "line": node.range.start_line if node.range else 1,
                "qualified_name": node.qualified_name or node.name,
            }
            if parent:
                data["parent"] = parent
            elements.append({"data": data})
            registered_node_ids.add(node.id)

    # Add edges with aggregation & rollup by (source, target, kind)
    grouped_edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edge in graph.edges:
        if edge.kind == "contains":
            continue

        src = edge.source
        tgt = edge.target

        # Check direct visibility
        if src in registered_node_ids and tgt in registered_node_ids:
            if flow_edge_pairs is not None and (src, tgt) not in flow_edge_pairs:
                continue

            key = (src, tgt, edge.kind)
            cnt = edge.count or 1
            if key not in grouped_edges:
                grouped_edges[key] = {
                    "source": src,
                    "target": tgt,
                    "kind": edge.kind,
                    "count": cnt,
                    "confidence": edge.confidence,
                    "is_reference": (edge.kind == "references"),
                }
            else:
                grouped_edges[key]["count"] += cnt

    edge_counter = 0
    for (src, tgt, kind), data in grouped_edges.items():
        edge_counter += 1
        count = data["count"]
        # Only show count label if there are multiple calls/invocations to avoid clutter
        label = f"{count} {kind}" if count > 1 else ""

        elements.append({
            "data": {
                "id": f"e_{edge_counter}_{src}_{tgt}_{kind}",
                "source": src,
                "target": tgt,
                "kind": kind,
                "count": count,
                "confidence": data["confidence"],
                "label": label,
                "is_reference": data["is_reference"],
            }
        })

    return elements


def generate_html_map(
    graph: Graph,
    out_file: Optional[Path | str] = None,
    show_noise: bool = False,
    show_manifests: bool = False,
    max_nodes: int = 60,
    flow_nodes: Optional[list[Node]] = None,
    flow_edges: Optional[list[Edge]] = None,
    include_helpers: bool = True,
) -> str:
    """Generate self-contained map.html with inlined Cytoscape stack, CSS, JS, and graph data."""
    view_tree = build_universal_view_tree(
        graph,
        show_noise=show_noise,
        show_manifests=show_manifests,
        max_nodes=max_nodes,
        include_helpers=include_helpers,
    )

    elements = convert_view_tree_to_cytoscape_elements(
        tree=view_tree,
        graph=graph,
        flow_nodes=flow_nodes,
        flow_edges=flow_edges,
    )

    # Load vendor assets
    cytoscape_js = _load_asset("cytoscape.min.js")
    layout_base_js = _load_asset("layout-base.js")
    cose_base_js = _load_asset("cose-base.js")
    fcose_js = _load_asset("cytoscape-fcose.js")
    expand_collapse_js = _load_asset("cytoscape-expand-collapse.js")
    viewer_css = _load_asset("viewer.css")
    viewer_js = _load_asset("viewer.js")

    target_name = graph.meta.get("target_path", "Project Architecture")
    subtitle = "Call Flow Trace" if flow_nodes else "Interactive Codebase Architecture"

    payload_json = json.dumps({
        "elements": elements,
        "meta": {
            "target_path": graph.meta.get("target_path", ""),
            "cartog_version": graph.meta.get("cartog_version", "0.1.0"),
            "is_flow": bool(flow_nodes),
        }
    }, indent=None, separators=(",", ":"))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cartog Interactive Map - {target_name}</title>
  <style>
{viewer_css}
  </style>
</head>
<body>
  <div id="app-container">
    <header id="header-bar">
      <div class="brand-section">
        <span class="brand-logo">&#9670; Cartog</span>
        <span class="project-title">{target_name} &bull; {subtitle}</span>
      </div>
      <div class="header-controls">
        <input type="text" id="search-input" class="search-box" placeholder="Filter symbols, files..." aria-label="Search">
        <select id="select-layout" class="select-ctrl" title="Layout Algorithm">
          <option value="fcose">Layout: Blueprint (fCoSE)</option>
          <option value="dag">Layout: Hierarchical (DAG)</option>
          <option value="grid">Layout: Grid</option>
        </select>
        <select id="select-routing" class="select-ctrl" title="Edge Routing Style">
          <option value="taxi">Edges: Orthogonal</option>
          <option value="straight">Edges: Straight</option>
          <option value="bezier">Edges: Curved</option>
        </select>
        <button id="btn-toggle-references" class="btn-ctrl" title="Toggle References Visibility">&#9678; References: Off</button>
        <button id="btn-toggle-helpers" class="btn-ctrl" title="Toggle Internal Helpers Visibility">&#9881; Helpers: Shown</button>
        <button id="btn-fit" class="btn-ctrl" title="Fit to Viewport">&#x2922; Fit</button>
        <button id="btn-expand-all" class="btn-ctrl" title="Expand All Compounds">&#x229E; Expand All</button>
        <button id="btn-collapse-all" class="btn-ctrl" title="Collapse All Compounds">&#x229F; Collapse All</button>
        <button id="btn-reset-layout" class="btn-ctrl" title="Recalculate Layout">&#8635; Redo</button>
      </div>
    </header>

    <div id="workspace">
      <div id="cy-container"></div>

      <!-- Floating Legend -->
      <div id="legend-panel">
        <div class="legend-title">Legend</div>
        <div class="legend-items">
          <div class="legend-item"><span class="legend-color-dot" style="background:#8957e5;"></span>Subsystem</div>
          <div class="legend-item"><span class="legend-edge-line" style="background:#58a6ff;"></span>Calls</div>
          <div class="legend-item"><span class="legend-color-dot" style="background:#3fb950;"></span>Folder</div>
          <div class="legend-item"><span class="legend-edge-line" style="background:#bc8cff; border-top:1px dotted #bc8cff; height:0;"></span>Imports</div>
          <div class="legend-item"><span class="legend-color-dot" style="background:#58a6ff;"></span>File</div>
          <div class="legend-item"><span class="legend-edge-line" style="background:#39c5bb; border-top:1px dashed #39c5bb; height:0;"></span>References</div>
          <div class="legend-item"><span class="legend-color-dot" style="background:#f0883e;"></span>Class</div>
          <div class="legend-item"><span class="legend-edge-line" style="background:#f0883e; border-top:1px dashed #f0883e; height:0;"></span>Overrides</div>
          <div class="legend-item"><span class="legend-color-dot" style="background:#d29922;"></span>Function</div>
          <div class="legend-item"><span class="legend-edge-line" style="background:#f778ba;"></span>Serves</div>
          <div class="legend-item"><span class="legend-color-dot" style="background:#f778ba;"></span>Route / Command</div>
        </div>
      </div>

      <!-- Sidebar for node details -->
      <aside id="sidebar" class="hidden">
        <div class="sidebar-header">
          <span class="sidebar-title">Symbol Inspector</span>
          <button id="btn-close-sidebar" class="sidebar-close-btn" title="Close Sidebar">&times;</button>
        </div>
        <div id="node-details" class="sidebar-body"></div>
      </aside>
    </div>
  </div>

  <!-- Inlined Cytoscape Stack & Runtime -->
  <script>
{cytoscape_js}
  </script>
  <script>
{layout_base_js}
  </script>
  <script>
{cose_base_js}
  </script>
  <script>
{fcose_js}
  </script>
  <script>
{expand_collapse_js}
  </script>
  <script>
    window.CARTOG_VIEW_DATA = {payload_json};
  </script>
  <script>
{viewer_js}
  </script>
</body>
</html>
"""

    if out_file:
        p = Path(out_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")

    return html
