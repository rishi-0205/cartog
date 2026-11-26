"""Service layer for transaction_db_service.

Part of the 'DB-TX-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.db_util import with_transaction
from src.repositories.match_repository import persist
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def transaction_db_service(input: object = None) -> dict:
    """Execute the transaction_db_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: DB-TX-01 — transaction_db_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("transaction_db_service: empty input, using defaults")
    try:
        return with_transaction(lambda: persist(data))
        hops.append("transaction_db_service")
        logger.info("{ 'name': 'transaction_db_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'transaction_db_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
