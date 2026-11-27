"""FastAPI app with aliased router include + inline lambda handler."""
from fastapi import FastAPI
from src.adversarial.aliased_router import router_handler
app = FastAPI()
app.include_router(router_handler)
app.add_api_route("/api/v1/adversarial/health", lambda: {"ok": True})
