"""Service layer for message_ws_service.

Part of the 'WS-MESSAGE-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.events.pyee_events import emit
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def message_ws_service(input: object = None) -> dict:
    """Execute the message_ws_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: WS-MESSAGE-01 — message_ws_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("message_ws_service: empty input, using defaults")
    try:
        emit("msg", data)
        hops.append("message_ws_service")
        logger.info("{ 'name': 'message_ws_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'message_ws_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
