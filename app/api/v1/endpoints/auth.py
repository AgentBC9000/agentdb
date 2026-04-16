from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

from app.core.security import generate_api_key, get_trial_expiry
from app.db.client import get_db
from app.core.dependencies import get_current_key

router = APIRouter()


class RegisterRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None


class RegisterResponse(BaseModel):
    api_key: str
    key_prefix: str
    tier: str
    trial_expires_at: str
    message: str


@router.post("/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, db=Depends(get_db)):
    agent_id = str(uuid.uuid4())
    raw_key, hashed_key = generate_api_key()
    key_prefix = raw_key[:12]
    trial_expiry = get_trial_expiry()

    await db.execute(
        "INSERT INTO agents (id, email, name) VALUES (:id, :email, :name)",
        {"id": agent_id, "email": payload.email, "name": payload.name}
    )

    await db.execute(
        """INSERT INTO api_keys
           (agent_id, key_hash, key_prefix, tier, trial_expires_at)
           VALUES (:agent_id, :key_hash, :key_prefix, 'trial', :trial_expires_at)""",
        {
            "agent_id": agent_id,
            "key_hash": hashed_key,
            "key_prefix": key_prefix,
            "trial_expires_at": trial_expiry,
        }
    )

    return RegisterResponse(
        api_key=raw_key,
        key_prefix=key_prefix,
        tier="trial",
        trial_expires_at=trial_expiry.isoformat(),
        message="Welcome to AgentDB. Your 3-day trial has started. Store your API key securely."
    )


@router.get("/me")
async def get_me(key_record=Depends(get_current_key)):
    return {
        "key_prefix": key_record["key_prefix"],
        "tier": key_record["tier"],
        "is_active": key_record["is_active"],
        "trial_expires_at": key_record.get("trial_expires_at"),
        "requests_today": key_record["requests_today"],
        "requests_total": key_record["requests_total"],
        "last_used_at": key_record["last_used_at"],
    }
