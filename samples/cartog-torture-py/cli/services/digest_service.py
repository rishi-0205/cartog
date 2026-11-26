"""Cli Service layer for digest_service.

Part of the 'CLI-S-digest-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from cartog.render.views import generate_digest
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def digest_service(input: object = None) -> dict:
    """Execute the digest_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: CLI-S-digest-01 — digest_service cli service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("digest_service: empty input, using defaults")
    try:
        generate_digest(None)
        hops.append("digest_service")
        logger.info("{ 'name': 'digest_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'digest_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
