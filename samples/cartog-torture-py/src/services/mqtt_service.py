"""Service layer for mqtt_service.

Part of the 'MQ-MQTT-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.mqtt import publish_mqtt
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def mqtt_service(input: object = None) -> dict:
    """Execute the mqtt_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-MQTT-01 — mqtt_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("mqtt_service: empty input, using defaults")
    try:
        publish_mqtt("topic", "payload")
        hops.append("mqtt_service")
        logger.info("{ 'name': 'mqtt_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'mqtt_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
