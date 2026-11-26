"""Service layer for read_file_service.

Part of the 'FILE-READ-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.file_util import read_config
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def read_file_service(input: object = None) -> dict:
    """Execute the read_file_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: FILE-READ-01 — read_file_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("read_file_service: empty input, using defaults")
    try:
        return read_config("config.yaml")
        hops.append("read_file_service")
        logger.info("{ 'name': 'read_file_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'read_file_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
