"""Service layer for kafka_producer_service.

Part of the 'MQ-KAFKA-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.kafka import send_kafka
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def kafka_producer_service(input: object = None) -> dict:
    """Execute the kafka_producer_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-KAFKA-01 — kafka_producer_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("kafka_producer_service: empty input, using defaults")
    try:
        await send_kafka("events", data)
        hops.append("kafka_producer_service")
        logger.info("{ 'name': 'kafka_producer_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'kafka_producer_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
