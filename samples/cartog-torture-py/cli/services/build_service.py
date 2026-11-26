"""Cli Service layer for build_service.

Part of the 'CLI-S-build-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.graph.merge import build_graph
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def build_service(input: object = None) -> dict:
    """Execute the build_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-build-01 — build_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("build_service: empty input, using defaults")
    try:
        build_graph([])
        hops.append("build_service")
        logger.info("{ 'name': 'build_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'build_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
