"""Service layer for redis_pub_service.

Part of the 'MQ-REDIS-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.redis_pubsub import publish
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def redis_pub_service(input: object = None) -> dict:
    """Execute the redis_pub_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-REDIS-01 — redis_pub_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("redis_pub_service: empty input, using defaults")
    try:
        publish("notifications", data)
        hops.append("redis_pub_service")
        logger.info("{ 'name': 'redis_pub_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'redis_pub_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
