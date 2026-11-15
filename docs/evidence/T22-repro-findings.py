"""Preserved reproduction script for findings F3, F4, and F5 (T22, 2026-11-12).

The original ran from `.scratch/repro_findings.py`; that path is deleted after the
task. This copy is kept for reproducibility and lives in `docs/evidence/` only.
Run it with the repo venv: `venv\\Scripts\\python.exe docs\\evidence\\T22-repro-findings.py`.

F1, F2, F6, F7, F8, and F9 are reproduced by the grep/command transcript in
`docs/evidence/T22-plan-restructure.txt`.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cartog.model import Graph, Node, Edge, SourceRange
from cartog.views import build_universal_view_tree
from cartog.export_html import convert_view_tree_to_cytoscape_elements


def banner(name: str) -> None:
    print()
    print("=" * 70)
    print(name)
    print("=" * 70)


def f3_dropped_edge() -> None:
    banner("F3: edges to collapsed helpers are dropped, not rolled up")
    g = Graph(meta={"target_path": "f3"})
    f1 = Node(id="file_core", name="core.py", qualified_name="core.py", kind="file", path="core.py")
    f2 = Node(id="file_util", name="util.py", qualified_name="util.py", kind="file", path="util.py")
    route = Node(id="fn_index", name="index", qualified_name="core:index", kind="route",
                 path="core.py", parent="file_core", attrs={"line": 3})
    helper = Node(id="fn_internal", name="_internal", qualified_name="core:_internal", kind="function",
                  path="core.py", parent="file_core", attrs={"line": 9})
    target = Node(id="fn_format", name="format", qualified_name="util:format", kind="function",
                  path="util.py", parent="file_util", attrs={"line": 2})
    for n in (f1, f2, route, helper, target):
        g.add_node(n)
    g.add_edge(Edge(source="fn_index", target="fn_format", kind="calls", confidence="resolved", count=1))
    g.add_edge(Edge(source="fn_index", target="fn_internal", kind="references", confidence="resolved", count=1))

    tree = build_universal_view_tree(g, include_helpers=False)
    elements = convert_view_tree_to_cytoscape_elements(tree, g)
    node_ids = {e["data"]["id"] for e in elements if "source" not in e["data"]}
    edge_pairs = [(e["data"]["source"], e["data"]["target"]) for e in elements if "source" in e["data"]]
    print("underlying graph edges :", len(g.edges))
    print("emitted cytoscape edges:", len(edge_pairs), edge_pairs)
    print("fn_internal registered :", "fn_internal" in node_ids)
    print("helper_group registered:", any(i.startswith("helpers_") for i in node_ids))
    print("edge fn_index -> fn_internal present:", ("fn_index", "fn_internal") in edge_pairs)


def f4_fallback_crash() -> None:
    banner("F4: raw-graph fallback raises TypeError on node.range[0]")
    g = Graph(meta={"target_path": "f4"})
    g.add_node(Node(id="orphan_fn", name="orphan", qualified_name="orphan.py:orphan", kind="function",
                    path="orphan.py", range=SourceRange(1, 0, 3, 0)))
    tree = build_universal_view_tree(g)
    print("view tree children:", len(tree.children))
    try:
        convert_view_tree_to_cytoscape_elements(tree, g)
        print("RESULT: no exception (finding NOT reproduced)")
    except Exception as exc:
        print(f"RESULT: {type(exc).__name__}: {exc}")


def f5_quadratic_add_edge() -> None:
    banner("F5: Graph.add_edge linear scan (O(E^2))")
    for n in (5000, 10000, 20000):
        g = Graph()
        nodes = [Node(id=f"n{i}", name=f"n{i}", qualified_name=f"n{i}", kind="function", path=f"f{i}.py")
                 for i in range(n + 1)]
        for node in nodes:
            g.add_node(node)
        edges = [Edge(source=f"n{i}", target=f"n{n}", kind="calls", confidence="resolved") for i in range(n)]
        start = time.perf_counter()
        for e in edges:
            g.add_edge(e)
        elapsed = time.perf_counter() - start
        print(f"edges={n:>6}  time={elapsed:7.3f}s  stored={len(g.edges)}")


def main() -> None:
    f3_dropped_edge()
    f4_fallback_crash()
    f5_quadratic_add_edge()


if __name__ == "__main__":
    main()
