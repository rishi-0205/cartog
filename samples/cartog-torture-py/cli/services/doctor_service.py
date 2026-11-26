"""Cli Service layer for doctor_service.

Part of the 'CLI-S-doctor-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.core.toolchain import check_toolchain
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def doctor_service(input: object = None) -> dict:
    """Execute the doctor_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-doctor-01 — doctor_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("doctor_service: empty input, using defaults")
    try:
        logger.info(str(check_toolchain()))
        hops.append("doctor_service")
        logger.info("{ 'name': 'doctor_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'doctor_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
