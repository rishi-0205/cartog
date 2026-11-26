"""Service layer for constructor_di_service.

Part of the 'DI-CONSTRUCTOR-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.di.injector_container import container_get
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def constructor_di_service(input: object = None) -> dict:
    """Execute the constructor_di_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: DI-CONSTRUCTOR-01 — constructor_di_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("constructor_di_service: empty input, using defaults")
    try:
        return container_get("Service")
        hops.append("constructor_di_service")
        logger.info("{ 'name': 'constructor_di_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'constructor_di_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
