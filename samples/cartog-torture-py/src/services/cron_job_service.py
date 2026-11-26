"""Service layer for cron_job_service.

Part of the 'SCHED-APS-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.repositories.match_repository import rebuild
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def cron_job_service(input: object = None) -> dict:
    """Execute the cron_job_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: SCHED-APS-01 — cron_job_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("cron_job_service: empty input, using defaults")
    try:
        return rebuild()
        hops.append("cron_job_service")
        logger.info("{ 'name': 'cron_job_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'cron_job_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
