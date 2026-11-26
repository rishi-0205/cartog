"""Service layer for interval_job_service.

Part of the 'SCHED-INTERVAL-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.cache_util import cache_set
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def interval_job_service(input: object = None) -> dict:
    """Execute the interval_job_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: SCHED-INTERVAL-01 — interval_job_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("interval_job_service: empty input, using defaults")
    try:
        cache_set("ttl", 1)
        hops.append("interval_job_service")
        logger.info("{ 'name': 'interval_job_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'interval_job_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
