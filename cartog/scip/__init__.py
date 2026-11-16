"""SCIP: the indexer runner, decoder, call linker, and generated bindings.

R8 turned the flat ``cartog.scip_pass`` / ``cartog.scip_pb2`` modules into this
package. ``cartog/scip/runner.py`` holds the pipeline, ``scip_pb2.py`` is
generated from ``scip.proto`` (do not edit), and ``windows_shim.js`` is the
Win32 Node preload fix.
"""

from __future__ import annotations

from cartog.scip.runner import (
    CallEdgeCandidate,
    ScipDocument,
    ScipIndexResult,
    ScipOccurrence,
    ScipRelationship,
    classify_occurrence,
    decode_scip_index,
    find_enclosing_symbol,
    get_indexer_env,
    link_calls,
    normalize_scip_range,
    run_scip_indexer,
    write_scip_json,
)

__all__ = [
    "CallEdgeCandidate",
    "ScipDocument",
    "ScipIndexResult",
    "ScipOccurrence",
    "ScipRelationship",
    "classify_occurrence",
    "decode_scip_index",
    "find_enclosing_symbol",
    "get_indexer_env",
    "link_calls",
    "normalize_scip_range",
    "run_scip_indexer",
    "write_scip_json",
]
