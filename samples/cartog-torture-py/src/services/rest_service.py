"""Service layer for rest_service.

Part of the 'RPC-REST-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.rpc.service_http import fetch_service
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def rest_service(input: object = None) -> dict:
    """Execute the rest_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: RPC-REST-01 — rest_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("rest_service: empty input, using defaults")
    try:
        return fetch_service("/users")
        hops.append("rest_service")
        logger.info("{ 'name': 'rest_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'rest_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
