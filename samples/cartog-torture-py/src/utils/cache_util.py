"""In-memory cache utility — cache spines. PATTERN: CACHE-UTIL-01."""
_store: dict[str, object] = {}

def cache_get(k: str) -> object:
    """Read a value from the cache."""
    return _store.get(k)

def cache_set(k: str, v: object) -> None:
    """Write a value to the cache."""
    _store[k] = v

def cache_del(k: str) -> None:
    """Invalidate a cache key."""
    _store.pop(k, None)

def cache_expire(k: str, ttl: int) -> None:
    """Set a TTL on a cache key."""
    _store[k] = ttl
