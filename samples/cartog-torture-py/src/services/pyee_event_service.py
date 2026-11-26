"""Service layer for pyee_event_service.

Part of the 'EVENT-PYEE-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.events.pyee_events import emit
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def pyee_event_service(input: object = None) -> dict:
    """Execute the pyee_event_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: EVENT-PYEE-01 — pyee_event_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("pyee_event_service: empty input, using defaults")
    try:
        emit("tick", data)
        hops.append("pyee_event_service")
        logger.info("{ 'name': 'pyee_event_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'pyee_event_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
