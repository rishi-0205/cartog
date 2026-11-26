"""Service layer for parameter_di_service.

Part of the 'DI-PARAMETER-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.di.fastapi_depends import provide
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def parameter_di_service(input: object = None) -> dict:
    """Execute the parameter_di_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: DI-PARAMETER-01 — parameter_di_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("parameter_di_service: empty input, using defaults")
    try:
        return provide()
        hops.append("parameter_di_service")
        logger.info("{ 'name': 'parameter_di_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'parameter_di_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
