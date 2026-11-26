"""Cli Service layer for scip_service.

Part of the 'CLI-S-scip-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.scip.runner import index_project
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def scip_service(input: object = None) -> dict:
    """Execute the scip_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-scip-01 — scip_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("scip_service: empty input, using defaults")
    try:
        await index_project("cartog-out")
        hops.append("scip_service")
        logger.info("{ 'name': 'scip_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'scip_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
