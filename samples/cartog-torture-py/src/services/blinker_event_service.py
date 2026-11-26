"""Service layer for blinker_event_service.

Part of the 'EVENT-BLINKER-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.events.blinker_signals import signal_send
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def blinker_event_service(input: object = None) -> dict:
    """Execute the blinker_event_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: EVENT-BLINKER-01 — blinker_event_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("blinker_event_service: empty input, using defaults")
    try:
        signal_send("tick", data)
        hops.append("blinker_event_service")
        logger.info("{ 'name': 'blinker_event_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'blinker_event_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
