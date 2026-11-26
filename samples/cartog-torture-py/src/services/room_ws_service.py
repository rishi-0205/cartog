"""Service layer for room_ws_service.

Part of the 'WS-ROOM-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.websocket.channels_consumer import broadcast
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def room_ws_service(input: object = None) -> dict:
    """Execute the room_ws_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: WS-ROOM-01 — room_ws_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("room_ws_service: empty input, using defaults")
    try:
        await broadcast("room", data)
        hops.append("room_ws_service")
        logger.info("{ 'name': 'room_ws_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'room_ws_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
