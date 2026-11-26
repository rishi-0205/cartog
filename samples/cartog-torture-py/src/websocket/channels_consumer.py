"""Django Channels async consumer — broadcast spine. PATTERN: WS-ROOM-01."""
from channels.generic.websocket import AsyncWebsocketConsumer

class Consumer(AsyncWebsocketConsumer):
    """Async WebSocket consumer."""
    async def receive(self, text_data=None):
        """Handle an incoming message."""
        await self.send(text_data)

async def broadcast(room: str, data: object) -> None:
    """Broadcast to a room."""
    return None
