"""Compatibility shim: this module moved to :mod:`cartog.core.config` in R5.

Import from ``cartog.core.config`` in new code.
"""

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
]
