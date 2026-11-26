"""Service layer for bg_job_service.

Part of the 'SCHED-BG-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.repositories.event_repository import save
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def bg_job_service(input: object = None) -> dict:
    """Execute the bg_job_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: SCHED-BG-01 — bg_job_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("bg_job_service: empty input, using defaults")
    try:
        return save()
        hops.append("bg_job_service")
        logger.info("{ 'name': 'bg_job_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'bg_job_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
