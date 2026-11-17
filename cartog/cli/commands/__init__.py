"""One module per CLI command; importing the package registers them all."""

from cartog.cli.commands import (  # noqa: F401  (registration side effects)
    build,
    check,
    digest,
    doctor,
    flow,
    map,
    parse,
    queries,
    scip,
    view,
)

__all__ = [
    "build",
    "check",
    "digest",
    "doctor",
    "flow",
    "map",
    "parse",
    "queries",
    "scip",
    "view",
]
