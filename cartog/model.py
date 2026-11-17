"""Compatibility shim: this module moved to :mod:`cartog.core.model` in R5.

Import from ``cartog.core.model`` in new code. The old path stays importable so
downstream scripts and tests keep working; the test
``test_public_imports_after_move`` asserts both paths expose the same objects.
"""

from cartog.core.model import (
    SCHEMA_VERSION,
    Edge,
    Graph,
    Location,
    ManifestFacts,
    Node,
    SourceRange,
    make_edge_id,
    make_node_id,
)

__all__ = [
    "SCHEMA_VERSION",
    "Edge",
    "Graph",
    "Location",
    "ManifestFacts",
    "Node",
    "SourceRange",
    "make_edge_id",
    "make_node_id",
]
