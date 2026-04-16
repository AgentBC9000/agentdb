from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from typing import Optional

from app.core.security import hash_api_key, is_trial_expired
from app.db.client import get_db

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_key(
    api_key: Optional[str] = Depends(api_key_header),
    db=Depends(get_db),
):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required.")

    hashed = hash_api_key(api_key)
    key_record = await db.fetch_one(
        "SELECT * FROM api_keys WHERE key_hash = :hash AND is_active = true",
        {"hash": hashed}
    )

    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")

    if key_record["tier"] == "trial":
        if is_trial_expired(key_record["trial_expires_at"]):
            raise HTTPException(
                status_code=402,
                detail="Trial expired. Subscribe at https://agentdb.ai/pricing"
            )

    return key_record


async def require_pro(key_record=Depends(get_current_key)):
    if key_record["tier"] not in ["pro", "fleet"]:
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires AgentDB Pro."
        )
    return key_record
