"""Controller for score_update — API spine. PATTERN: API-SCORE_UPDATE-01."""
from src.services.match_service import match_service

async def score_update_controller(payload: object = None) -> dict:
    """Delegate to the match service."""
    return await match_service(payload)
