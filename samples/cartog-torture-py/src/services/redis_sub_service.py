"""Service layer for redis_sub_service.

Part of the 'MQ-REDIS-02' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.redis_pubsub import subscribe
from src.repositories.event_repository import save
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def redis_sub_service(input: object = None) -> dict:
    """Execute the redis_sub_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-REDIS-02 — redis_sub_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("redis_sub_service: empty input, using defaults")
    try:
        subscribe("notifications")
        return save()
        hops.append("redis_sub_service")
        logger.info("{ 'name': 'redis_sub_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'redis_sub_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
