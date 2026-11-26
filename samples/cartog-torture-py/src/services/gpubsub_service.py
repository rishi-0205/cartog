"""Service layer for gpubsub_service.

Part of the 'MQ-GCP-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.gcp_pubsub import publish_gcp
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def gpubsub_service(input: object = None) -> dict:
    """Execute the gpubsub_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-GCP-01 — gpubsub_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("gpubsub_service: empty input, using defaults")
    try:
        publish_gcp("topic", data)
        hops.append("gpubsub_service")
        logger.info("{ 'name': 'gpubsub_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'gpubsub_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
