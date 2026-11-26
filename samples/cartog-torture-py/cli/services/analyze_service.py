"""Cli Service layer for analyze_service.

Part of the 'CLI-S-analyze-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.scip.runner import index_project
from cartog.graph.merge import build_graph
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def analyze_service(input: object = None) -> dict:
    """Execute the analyze_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-analyze-01 — analyze_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("analyze_service: empty input, using defaults")
    try:
        await index_project(out)
        g = build_graph([])
        logger.info(f"nodes={len(g.nodes)}")
        hops.append("analyze_service")
        logger.info("{ 'name': 'analyze_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'analyze_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
