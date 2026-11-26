"""Service layer for kafka_consumer_service.

Part of the 'MQ-KAFKA-02' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.kafka import consume
from src.repositories.event_repository import save
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def kafka_consumer_service(input: object = None) -> dict:
    """Execute the kafka_consumer_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-KAFKA-02 — kafka_consumer_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("kafka_consumer_service: empty input, using defaults")
    try:
        for msg in consume("events"):
            save(msg)
        return None
        hops.append("kafka_consumer_service")
        logger.info("{ 'name': 'kafka_consumer_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'kafka_consumer_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
