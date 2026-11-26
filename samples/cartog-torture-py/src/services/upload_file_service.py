"""Service layer for upload_file_service.

Part of the 'FILE-UPLOAD-01' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
from src.utils.s3_util import put_object
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def upload_file_service(input: object = None) -> dict:
    """Execute the upload_file_service workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: FILE-UPLOAD-01 — upload_file_service service call chain
    hops: list[str] = []
    if input is None:
        logger.warning("upload_file_service: empty input, using defaults")
    try:
        put_object("key", "body")
        hops.append("upload_file_service")
        logger.info("{ 'name': 'upload_file_service', 'hops': len(hops) }")
        return {"ok": True, "hops": hops}
    except Exception as exc:
        logger.error("{ 'err': exc, 'name': 'upload_file_service' }")
        return {"ok": False, "hops": hops, "error": str(exc)}
