# PATTERN: MIDDLEWARE-FASTAPI-01 — @app.middleware
from fastapi import FastAPI
app = FastAPI()
@app.middleware("http")
async def mw(request, call_next): return await call_next(request)
