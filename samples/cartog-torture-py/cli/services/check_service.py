"""Cli Service layer for check_service.

Part of the 'CLI-S-check-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.graph.validate import validate_graph
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def check_service(input: object = None) -> dict:
    """Execute the check_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-check-01 — check_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("check_service: empty input, using defaults")
    try:
        errors = validate_graph(None)
        logger.info(f"errors={len(errors)}")
        hops.append("check_service")
        logger.info("{ 'name': 'check_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'check_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
