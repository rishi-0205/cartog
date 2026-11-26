"""Service layer for beat_job_service.

Part of the 'SCHED-BEAT-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.queues.celery_app import send_task
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def beat_job_service(input: object = None) -> dict:
    """Execute the beat_job_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: SCHED-BEAT-01 — beat_job_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("beat_job_service: empty input, using defaults")
    try:
        send_task("score.persist", [data])
        hops.append("beat_job_service")
        logger.info("{ 'name': 'beat_job_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'beat_job_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
