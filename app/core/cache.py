import redis.asyncio as redis
import json
import hashlib
from typing import Any, Optional
from app.core.config import settings


# ─── Redis Client ──────────────────────────────────────────────────────────
redis_client: redis.Redis = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


# ─── Cache Helpers ─────────────────────────────────────────────────────────

def make_key(prefix: str, *args) -> str:
    """Generate a consistent cache key."""
    raw = ":".join(str(a) for a in args)
    hashed = hashlib.md5(raw.encode()).hexdigest()
    return f"{prefix}:{hashed}"


async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache. Returns None if miss."""
    try:
        r = await get_redis()
        value = await r.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        print(f"[CACHE] GET error: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Set value in cache with TTL in seconds."""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        print(f"[CACHE] SET error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete a single key."""
    try:
        r = await get_redis()
        await r.delete(key)
        return True
    except Exception as e:
        print(f"[CACHE] DELETE error: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    try:
        r = await get_redis()
        keys = await r.keys(pattern)
        if keys:
            return await r.delete(*keys)
        return 0
    except Exception as e:
        print(f"[CACHE] DELETE PATTERN error: {e}")
        return 0