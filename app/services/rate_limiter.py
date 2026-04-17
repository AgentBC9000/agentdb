from fastapi import HTTPException
import redis.asyncio as redis
from app.core.config import settings
from app.models.api_key import APIKeyTier

RATE_LIMITS = {
    APIKeyTier.TRIAL: settings.RATE_LIMIT_TRIAL,   # 100/day
    APIKeyTier.BASIC: settings.RATE_LIMIT_BASIC,   # 1000/day
    APIKeyTier.PRO:   settings.RATE_LIMIT_PRO,     # unlimited
    APIKeyTier.FLEET: settings.RATE_LIMIT_PRO,
}

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def check_rate_limit(key_record: dict):
    """
    Check and increment rate limit for the given API key.
    Uses Redis with a daily TTL window.
    If Redis is unavailable, fails open (allows the request).
    """
    tier = key_record["tier"]
    limit = RATE_LIMITS.get(tier, 100)

    if limit >= 99999:
        return  # Unlimited tier

    try:
        r = await get_redis()
        redis_key = f"ratelimit:{key_record['id']}:{__import__('datetime').date.today()}"

        current = await r.incr(redis_key)

        if current == 1:
            await r.expire(redis_key, 86400)

        if current > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Daily rate limit reached ({limit} requests). Resets at midnight UTC. Upgrade at https://agentdb.ai/pricing",
                headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"}
            )
    except HTTPException:
        raise
    except Exception:
        # Redis unavailable — fail open, don't block the request
        pass
