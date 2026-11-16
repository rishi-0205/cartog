"""Compatibility shim: this module moved to :mod:`cartog.scan.cache` in R6.

Import from ``cartog.scan.cache`` in new code.
"""

from cartog.scan.cache import DEFAULT_EXTRACTOR_SCHEMA_VERSION, ParseCache

__all__ = ["DEFAULT_EXTRACTOR_SCHEMA_VERSION", "ParseCache"]
