"""Service layer for read_cache_service.

Part of the 'CACHE-READ-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.cache_util import cache_get, cache_set
from src.repositories.match_repository import find
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def read_cache_service(input: object = None) -> dict:
    """Execute the read_cache_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CACHE-READ-01 — read_cache_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("read_cache_service: empty input, using defaults")
    try:
        v = cache_get("k")
        if v is None:
            cache_set("k", find())
        hops.append("read_cache_service")
        logger.info("{ 'name': 'read_cache_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'read_cache_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
