"""FastAPI routes — API-S1, API-S2. PATTERN: ROUTE-FASTAPI-01."""
from fastapi import FastAPI, APIRouter, Depends
from src.controllers.score_update_controller import score_update_controller
from src.controllers.user_controller import user_controller

app = FastAPI()
router = APIRouter()

@app.post("/api/v1/match/score_update")
async def score_update(payload: dict, dep=Depends(provide)) -> dict:
    """Score update endpoint with DI dependency (must emit decorator ref)."""
    return await score_update_controller(payload)

@app.get("/api/v1/users")
async def users() -> dict:
    """List users endpoint."""
    return user_controller()

router.get("/api/v1/health")(health)
app.include_router(router)

def health() -> dict:
    """Health check."""
    return {"ok": True}

def provide() -> object:
    """DI provider."""
    return object()
