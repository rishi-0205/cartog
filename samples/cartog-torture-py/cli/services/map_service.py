"""Cli Service layer for map_service.

Part of the 'CLI-S-map-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.render.views import trace_call_flow
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def map_service(input: object = None) -> dict:
    """Execute the map_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-map-01 — map_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("map_service: empty input, using defaults")
    try:
        trace_call_flow(None)
        hops.append("map_service")
        logger.info("{ 'name': 'map_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'map_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
