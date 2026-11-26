# PATTERN: MIDDLEWARE-ASGI-01 — ASGI middleware class
class ASGIMiddleware:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send): await self.app(scope, receive, send)
