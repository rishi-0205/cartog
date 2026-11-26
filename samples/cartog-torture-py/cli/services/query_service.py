"""Cli Service layer for query_service.

Part of the 'CLI-S-query-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.render.views import generate_digest
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def query_service(input: object = None) -> dict:
    """Execute the query_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-query-01 — query_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("query_service: empty input, using defaults")
    try:
        generate_digest(None)
        hops.append("query_service")
        logger.info("{ 'name': 'query_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'query_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
