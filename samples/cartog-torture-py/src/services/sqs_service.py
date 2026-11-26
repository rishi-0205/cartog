"""Service layer for sqs_service.

Part of the 'MQ-SQS-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.sqs import send_sqs
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def sqs_service(input: object = None) -> dict:
    """Execute the sqs_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: MQ-SQS-01 — sqs_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("sqs_service: empty input, using defaults")
    try:
        send_sqs("body")
        hops.append("sqs_service")
        logger.info("{ 'name': 'sqs_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'sqs_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
