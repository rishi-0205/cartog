"""Controller for user — API spine. PATTERN: API-USER-01."""
from src.services.user_service import user_service

async def user_controller(payload: object = None) -> dict:
    """Delegate to the user service."""
    return await user_service(payload)
