"""Service layer for health_service.

Part of the 'API-S6' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.cache_util import cache_get
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def health_service(input: object = None) -> dict:
    """Execute the health_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: API-S6 — health_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("health_service: empty input, using defaults")
    try:
        return cache_get("health")
        hops.append("health_service")
        logger.info("{ 'name': 'health_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'health_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
