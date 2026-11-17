"""Compatibility shim: the adapter registry moved to :mod:`cartog.parse` in R7.

Import from ``cartog.parse`` (or ``cartog.parse.base`` and friends) in new code.
"""

from cartog.parse import (
    LanguageAdapter,
    ParseFileResult,
    get_adapter,
    get_adapter_for_path,
    parse_source_file,
)

__all__ = [
    "LanguageAdapter",
    "ParseFileResult",
    "get_adapter",
    "get_adapter_for_path",
    "parse_source_file",
]
