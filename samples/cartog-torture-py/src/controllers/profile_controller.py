"""Controller for profile — API spine. PATTERN: API-PROFILE-01."""
from src.services.profile_service import profile_service

async def profile_controller(payload: object = None) -> dict:
    """Delegate to the profile service."""
    return await profile_service(payload)
