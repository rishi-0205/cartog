"""Graph assembly and validation.

R9 moved ``cartog.merge`` and ``cartog.validate`` here. Callers can import from
``cartog.graph`` or from the two modules directly; the old flat paths remain as
shims.
"""

from __future__ import annotations

from cartog.graph.merge import build_graph
from cartog.graph.validate import (
    CrossCheckResult,
    MismatchRecord,
    ValidationResult,
    cross_check_imports_and_calls,
    validate_graph,
    validate_ranges_and_containment,
)

__all__ = [
    "CrossCheckResult",
    "MismatchRecord",
    "ValidationResult",
    "build_graph",
    "cross_check_imports_and_calls",
    "validate_graph",
    "validate_ranges_and_containment",
]
