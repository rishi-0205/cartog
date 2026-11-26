"""Service layer for profile_service.

Part of the 'API-S3' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.rabbitmq import basic_publish
from src.repositories.user_repository import find
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def profile_service(input: object = None) -> dict:
    """Execute the profile_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: API-S3 — profile_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("profile_service: empty input, using defaults")
    try:
        basic_publish("q1", data)
        return find()
        hops.append("profile_service")
        logger.info("{ 'name': 'profile_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'profile_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
