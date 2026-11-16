"""Rendering: view selection, JSON/Mermaid/HTML exporters, and bundled assets.

R10 moved ``cartog.views`` and the three exporters here; ``view_assets/`` became
``render/assets/``. The old flat module paths stay as shims.
"""

from __future__ import annotations

from cartog.render.views import (
    CallCounts,
    NoiseCategory,
    NoiseClassification,
    ViewNode,
    build_universal_view_tree,
    classify_boundary_functions,
    detect_noise_files,
    find_flow_candidates,
    generate_digest,
    get_call_counts,
    rewire_view_edges,
    trace_call_flow,
)

__all__ = [
    "CallCounts",
    "NoiseCategory",
    "NoiseClassification",
    "ViewNode",
    "build_universal_view_tree",
    "classify_boundary_functions",
    "detect_noise_files",
    "find_flow_candidates",
    "generate_digest",
    "get_call_counts",
    "rewire_view_edges",
    "trace_call_flow",
]
