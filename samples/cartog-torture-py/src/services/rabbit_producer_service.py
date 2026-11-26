"""Service layer for rabbit_producer_service.

Part of the 'MQ-RABBITMQ-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.rabbitmq import basic_publish
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def rabbit_producer_service(input: object = None) -> dict:
    """Execute the rabbit_producer_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-RABBITMQ-01 — rabbit_producer_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("rabbit_producer_service: empty input, using defaults")
    try:
        basic_publish("q1", data)
        hops.append("rabbit_producer_service")
        logger.info("{ 'name': 'rabbit_producer_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'rabbit_producer_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
