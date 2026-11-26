"""Redis pub/sub — publish/subscribe methods. PATTERN: MQ-REDIS-01."""
import redis

r = redis.Redis()

def publish(ch: str, data: object) -> None:
    """Publish to a channel."""
    r.publish(ch, str(data))

def subscribe(ch: str) -> None:
    """Subscribe to a channel."""
    ps = r.pubsub()
    ps.subscribe(ch)
