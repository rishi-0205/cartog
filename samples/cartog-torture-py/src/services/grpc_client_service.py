"""Service layer for grpc_client_service.

Part of the 'RPC-GRPC-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.rpc.grpc_stub import call_grpc
from src.repositories.user_repository import find
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def grpc_client_service(input: object = None) -> dict:
    """Execute the grpc_client_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: RPC-GRPC-01 — grpc_client_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("grpc_client_service: empty input, using defaults")
    try:
        call_grpc()
        return find()
        hops.append("grpc_client_service")
        logger.info("{ 'name': 'grpc_client_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'grpc_client_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
