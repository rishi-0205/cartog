"""Service layer for query_db_service.

Part of the 'DB-QUERY-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.repositories.match_repository import find
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def query_db_service(input: object = None) -> dict:
    """Execute the query_db_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: DB-QUERY-01 — query_db_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("query_db_service: empty input, using defaults")
    try:
        return find()
        hops.append("query_db_service")
        logger.info("{ 'name': 'query_db_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'query_db_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
