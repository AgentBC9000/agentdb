from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

from app.core.config import settings
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


@router.post("/admin/upgrade-key")
async def upgrade_key(
    key_prefix: str = Query(..., description="Key prefix to upgrade"),
    tier: str = Query("pro", description="Target tier: trial, pro, fleet"),
    secret: Optional[str] = Query(None),
    db=Depends(get_db),
):
    """Admin endpoint — upgrade an API key's tier."""
    if secret != settings.ADMIN_SECRET.strip():
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    if tier not in ("trial", "pro", "fleet"):
        raise HTTPException(status_code=400, detail="Invalid tier")

    row = await db.fetch_one(
        "SELECT key_prefix, tier FROM api_keys WHERE key_prefix = :prefix",
        {"prefix": key_prefix},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")

    await db.execute(
        "UPDATE api_keys SET tier = :tier, trial_expires_at = NULL WHERE key_prefix = :prefix",
        {"tier": tier, "prefix": key_prefix},
    )
    return {"key_prefix": key_prefix, "tier": tier, "message": f"Key upgraded to {tier}"}


@router.post("/admin/migrate")
async def run_migration(
    secret: Optional[str] = Query(None),
    db=Depends(get_db),
):
    """Admin endpoint — run pending DB migrations."""
    if secret != settings.ADMIN_SECRET.strip():
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    migrations = []

    # Add podcast to content_type CHECK constraint
    try:
        await db.execute("""
            ALTER TABLE knowledge
            DROP CONSTRAINT IF EXISTS knowledge_content_type_check
        """)
        await db.execute("""
            ALTER TABLE knowledge
            ADD CONSTRAINT knowledge_content_type_check
            CHECK (content_type IN ('article', 'video', 'data', 'research', 'podcast'))
        """)
        migrations.append("✅ Added 'podcast' to content_type constraint")
    except Exception as exc:
        migrations.append(f"⚠️ content_type constraint: {exc}")

    return {"migrations": migrations}


@router.get("/admin/stats")
async def get_stats(
    secret: Optional[str] = Query(None),
    db=Depends(get_db),
):
    """Admin endpoint — subscriber counts and usage stats."""
    if secret != settings.ADMIN_SECRET.strip():
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    tiers = await db.fetch_all(
        """SELECT tier, COUNT(*) as count, SUM(requests_total) as total_requests
           FROM api_keys WHERE is_active = true GROUP BY tier ORDER BY tier"""
    )

    recent = await db.fetch_all(
        """SELECT key_prefix, tier, requests_today, requests_total, last_used_at::text
           FROM api_keys WHERE is_active = true
           ORDER BY last_used_at DESC NULLS LAST LIMIT 10"""
    )

    knowledge_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM knowledge WHERE is_active = true"
    )

    return {
        "subscribers": {row["tier"]: {"count": row["count"], "total_requests": row["total_requests"] or 0} for row in tiers},
        "total_subscribers": sum(row["count"] for row in tiers),
        "total_knowledge_items": knowledge_count["count"],
        "recent_users": [dict(r) for r in recent],
    }


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
