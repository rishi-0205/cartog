"""Service layer for nats_service.

Part of the 'MQ-NATS-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.nats import publish_nats
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def nats_service(input: object = None) -> dict:
    """Execute the nats_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-NATS-01 — nats_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("nats_service: empty input, using defaults")
    try:
        publish_nats("subject", data)
        hops.append("nats_service")
        logger.info("{ 'name': 'nats_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'nats_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
