"""Filesystem scanning: walking, ignore rules, the AST cache, and manifests.

`cartog.scan` used to be a single module. R6 turned it into this package:
:mod:`cartog.scan.walk` holds the walker, :mod:`cartog.scan.cache` the parse
cache, and :mod:`cartog.scan.manifests` the manifest parsers. The package
re-exports the walker's public names so ``from cartog.scan import walk_files``
keeps working.
"""

from __future__ import annotations

from cartog.scan.walk import (
    LANG_EXTENSIONS,
    FileInfo,
    IgnoreMetrics,
    ScanResult,
    SkippedFile,
    compute_ignore_hash,
    detect_language,
    detect_roots,
    hash_file,
    is_binary_file,
    walk_files,
)

__all__ = [
    "LANG_EXTENSIONS",
    "FileInfo",
    "IgnoreMetrics",
    "ScanResult",
    "SkippedFile",
    "compute_ignore_hash",
    "detect_language",
    "detect_roots",
    "hash_file",
    "is_binary_file",
    "walk_files",
]
