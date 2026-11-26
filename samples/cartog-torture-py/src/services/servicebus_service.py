"""Service layer for servicebus_service.

Part of the 'MQ-AZURE-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.azure_service_bus import send_azure
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def servicebus_service(input: object = None) -> dict:
    """Execute the servicebus_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-AZURE-01 — servicebus_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("servicebus_service: empty input, using defaults")
    try:
        send_azure("queue", data)
        hops.append("servicebus_service")
        logger.info("{ 'name': 'servicebus_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'servicebus_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
