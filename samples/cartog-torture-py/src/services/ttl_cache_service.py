"""Service layer for ttl_cache_service.

Part of the 'CACHE-TTL-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.cache_util import cache_expire
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def ttl_cache_service(input: object = None) -> dict:
    """Execute the ttl_cache_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CACHE-TTL-01 — ttl_cache_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("ttl_cache_service: empty input, using defaults")
    try:
        cache_expire("k", 60)
        hops.append("ttl_cache_service")
        logger.info("{ 'name': 'ttl_cache_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'ttl_cache_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
