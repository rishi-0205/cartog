"""Cli Service layer for parse_service.

Part of the 'CLI-S-parse-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.parse.python_adapter import PythonAdapter
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def parse_service(input: object = None) -> dict:
    """Execute the parse_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-parse-01 — parse_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("parse_service: empty input, using defaults")
    try:
        adapter = PythonAdapter()
        logger.info(adapter.name)
        hops.append("parse_service")
        logger.info("{ 'name': 'parse_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'parse_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
