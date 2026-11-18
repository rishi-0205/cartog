"""Command Line Interface for Cartog.

R11 split the flat ``cartog.cli`` module into this package: :mod:`cartog.cli.shared`
owns the Typer app and the helpers, :mod:`cartog.cli.commands` holds one module
per command. ``cartog.cli.app`` is the console entry point (``cartog.cli:app``).

The command names, flags, help text, and exit codes are unchanged.
"""

from __future__ import annotations

from cartog.cli.commands import (  # noqa: F401  (import registers the commands)
    analyze,
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
from cartog.cli.shared import (
    _execute_parse,
    _format_scip_fail_line,
    _resolve_graph,
    _resolve_scip,
    app,
    console,
)

__all__ = [
    "_execute_parse",
    "_format_scip_fail_line",
    "_resolve_graph",
    "_resolve_scip",
    "app",
    "console",
]
