"""Service layer for django_event_service.

Part of the 'EVENT-DJANGO-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.events.django_signals import django_send
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def django_event_service(input: object = None) -> dict:
    """Execute the django_event_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: EVENT-DJANGO-01 — django_event_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("django_event_service: empty input, using defaults")
    try:
        django_send("signal", data)
        hops.append("django_event_service")
        logger.info("{ 'name': 'django_event_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'django_event_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
