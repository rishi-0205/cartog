"""Service layer for match_service.

Part of the 'API-S1' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.celery_app import send_task
from src.queues.redis_pubsub import publish
from src.websocket.channels_consumer import broadcast
from src.repositories.match_repository import persist
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def match_service(input: object = None) -> dict:
    """Execute the match_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: API-S1 — match_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("match_service: empty input, using defaults")
    try:
        send_task("score.persist", [data])
        publish("notifications", data)
        await broadcast("room", data)
        return persist(data)
        hops.append("match_service")
        logger.info("{ 'name': 'match_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'match_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
