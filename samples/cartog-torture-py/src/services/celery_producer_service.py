"""Service layer for celery_producer_service.

Part of the 'MQ-CELERY-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.celery_app import send_task, delay_task, apply_async_task
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def celery_producer_service(input: object = None) -> dict:
    """Execute the celery_producer_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-CELERY-01 — celery_producer_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("celery_producer_service: empty input, using defaults")
    try:
        send_task("score.persist", [data])
        delay_task(data)
        apply_async_task(data)
        hops.append("celery_producer_service")
        logger.info("{ 'name': 'celery_producer_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'celery_producer_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
