"""Service layer for graphql_service.

Part of the 'RPC-GRAPHQL-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.rpc.graphql_resolvers import resolve_user
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def graphql_service(input: object = None) -> dict:
    """Execute the graphql_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: RPC-GRAPHQL-01 — graphql_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("graphql_service: empty input, using defaults")
    try:
        return resolve_user()
        hops.append("graphql_service")
        logger.info("{ 'name': 'graphql_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'graphql_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
