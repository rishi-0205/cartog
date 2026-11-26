"""Service layer for user_service.

Part of the 'API-S2' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.redis_pubsub import publish
from src.repositories.user_repository import find
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def user_service(input: object = None) -> dict:
    """Execute the user_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: API-S2 — user_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("user_service: empty input, using defaults")
    try:
        publish("user-events", data)
        return find()
        hops.append("user_service")
        logger.info("{ 'name': 'user_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'user_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
