"""Core types: the graph data model, configuration constants, and JSONC loading.

Moved here from the flat ``cartog.model``, ``cartog.config`` and
``cartog.jsonc`` modules in R5. Those paths survive as re-export shims.
"""

from __future__ import annotations

from cartog.core.config import (
    DEFAULT_CACHE_DIR,
    DEFAULT_IGNORED_DIRS,
    DEFAULT_IGNORED_GLOBS,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_OUT_DIR,
    SCHEMA_VERSION,
    SUPPORTED_LANGUAGES,
)
from cartog.core.jsonc import (
    JsoncParseError,
    load_jsonc_file,
    load_strict_json_file,
    strip_jsonc_comments_and_trailing_commas,
)
from cartog.core.model import (
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
    "DEFAULT_CACHE_DIR",
    "DEFAULT_IGNORED_DIRS",
    "DEFAULT_IGNORED_GLOBS",
    "DEFAULT_MAX_FILE_SIZE",
    "DEFAULT_MAX_FILE_SIZE_BYTES",
    "DEFAULT_MAX_FILE_SIZE_MB",
    "DEFAULT_OUT_DIR",
    "SCHEMA_VERSION",
    "SUPPORTED_LANGUAGES",
    "Edge",
    "Graph",
    "JsoncParseError",
    "Location",
    "ManifestFacts",
    "Node",
    "SourceRange",
    "load_jsonc_file",
    "load_strict_json_file",
    "make_edge_id",
    "make_node_id",
    "strip_jsonc_comments_and_trailing_commas",
]
