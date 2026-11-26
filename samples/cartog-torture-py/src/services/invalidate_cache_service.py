"""Service layer for invalidate_cache_service.

Part of the 'CACHE-INVALIDATE-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.cache_util import cache_del
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def invalidate_cache_service(input: object = None) -> dict:
    """Execute the invalidate_cache_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CACHE-INVALIDATE-01 — invalidate_cache_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("invalidate_cache_service: empty input, using defaults")
    try:
        cache_del("k")
        hops.append("invalidate_cache_service")
        logger.info("{ 'name': 'invalidate_cache_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'invalidate_cache_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
