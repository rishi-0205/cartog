"""Cli Service layer for flow_service.

Part of the 'CLI-S-flow-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.render.views import trace_call_flow
from cartog.render.export_mermaid import export_mermaid
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def flow_service(input: object = None) -> dict:
    """Execute the flow_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-flow-01 — flow_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("flow_service: empty input, using defaults")
    try:
        t = trace_call_flow(None)
        export_mermaid(t)
        hops.append("flow_service")
        logger.info("{ 'name': 'flow_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'flow_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
