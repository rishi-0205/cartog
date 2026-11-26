"""Service layer for admin_service.

Part of the 'API-S5' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.kafka import send_kafka
from src.repositories.admin_repository import rebuild
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def admin_service(input: object = None) -> dict:
    """Execute the admin_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: API-S5 — admin_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("admin_service: empty input, using defaults")
    try:
        await send_kafka("events", data)
        return rebuild()
        hops.append("admin_service")
        logger.info("{ 'name': 'admin_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'admin_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
