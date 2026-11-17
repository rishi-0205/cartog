"""Compatibility shim: this module moved to :mod:`cartog.core.jsonc` in R5.

Import from ``cartog.core.jsonc`` in new code.
"""

from cartog.core.jsonc import (
    JsoncParseError,
    load_jsonc_file,
    load_strict_json_file,
    strip_jsonc_comments_and_trailing_commas,
)

__all__ = [
    "JsoncParseError",
    "load_jsonc_file",
    "load_strict_json_file",
    "strip_jsonc_comments_and_trailing_commas",
]
