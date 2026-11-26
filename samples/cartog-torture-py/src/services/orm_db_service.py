"""Service layer for orm_db_service.

Part of the 'DB-ORM-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.orm_util import orm_find
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def orm_db_service(input: object = None) -> dict:
    """Execute the orm_db_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: DB-ORM-01 — orm_db_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("orm_db_service: empty input, using defaults")
    try:
        return orm_find()
        hops.append("orm_db_service")
        logger.info("{ 'name': 'orm_db_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'orm_db_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
