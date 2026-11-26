"""Service layer for celery_consumer_service.

Part of the 'MQ-CELERY-02' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.repositories.match_repository import persist
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def celery_consumer_service(input: object = None) -> dict:
    """Execute the celery_consumer_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-CELERY-02 — celery_consumer_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("celery_consumer_service: empty input, using defaults")
    try:
        return persist(data)
        hops.append("celery_consumer_service")
        logger.info("{ 'name': 'celery_consumer_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'celery_consumer_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
