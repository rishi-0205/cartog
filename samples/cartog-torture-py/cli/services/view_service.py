"""Cli Service layer for view_service.

Part of the 'CLI-S-view-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.render.export_html import export_html
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def view_service(input: object = None) -> dict:
    """Execute the view_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-view-01 — view_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("view_service: empty input, using defaults")
    try:
        html = await export_html()
        logger.info(f"bytes={len(html)}")
        hops.append("view_service")
        logger.info("{ 'name': 'view_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'view_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
