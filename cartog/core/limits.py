"""Configurable analysis limits that stop a run instead of truncating it (S8).

A hostile or accidental repository can be enormous. These limits bound the
work Cartog will start: the number of discovered source files, and the size of
the merged graph. When one is exceeded the run fails with a message naming the
limit and the flag that raises it; partial output is not published.

File *size* is a different kind of limit: files above ``--max-file-size`` are
excluded before parsing and listed in ``parse.json``/``meta.json`` as skipped,
which is advertised rather than silent. The values below are hard stops.
"""

from __future__ import annotations

#: Maximum source files discovered in one run before parsing starts.
DEFAULT_MAX_FILES = 50_000

#: Maximum nodes in the merged graph.
DEFAULT_MAX_GRAPH_NODES = 200_000

#: Maximum edges in the merged graph.
DEFAULT_MAX_GRAPH_EDGES = 500_000


class AnalysisLimitError(RuntimeError):
    """A configured analysis limit was exceeded; the run must stop."""


def enforce_file_count(count: int, limit: int) -> None:
    """Raise when more than ``limit`` source files were discovered."""
    if count > limit:
        raise AnalysisLimitError(
            f"file limit exceeded: discovered {count} source files, "
            f"limit is {limit} (raise it with --max-files)"
        )


def enforce_graph_size(
    node_count: int,
    edge_count: int,
    *,
    max_nodes: int,
    max_edges: int,
) -> None:
    """Raise when the merged graph exceeds the node or edge limit."""
    if node_count > max_nodes:
        raise AnalysisLimitError(
            f"graph node limit exceeded: built {node_count} nodes, "
            f"limit is {max_nodes} (raise it with --max-graph-nodes)"
        )
    if edge_count > max_edges:
        raise AnalysisLimitError(
            f"edge limit exceeded: built {edge_count} edges, "
            f"limit is {max_edges} (raise it with --max-graph-edges)"
        )
