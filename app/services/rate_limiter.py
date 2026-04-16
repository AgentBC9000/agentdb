from fastapi import HTTPException
import redis.asyncio as redis
from app.core.config import settings

RATE_LIMITS = {
    "trial": 100,
    "basic": 1000,
    "pro":   99999,
    "fleet": 99999,
}

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def check_rate_limit(key_record: dict):
    tier = key_record["tier"]
    limit = RATE_LIMITS.get(tier, 100)

    if limit >= 99999:
        return

    r = await get_redis()
    import datetime
    redis_key = f"ratelimit:{key_record['id']}:{datetime.date.today()}"

    current = await r.incr(redis_key)

    if current == 1:
        await r.expire(redis_key, 86400)

    if current > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily rate limit reached ({limit} requests). Upgrade at https://agentdb.ai/pricing",
            headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"}
        )
