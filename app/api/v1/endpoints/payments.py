from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.dependencies import get_current_key
from app.services.payment_service import (
    initiate_stripe_checkout,
    initiate_crypto_payment,
    get_billing_portal_url,
)

router = APIRouter()


class CheckoutRequest(BaseModel):
    provider: str = "stripe"
    tier: str = "basic"
    email: Optional[str] = None


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutRequest,
    key_record=Depends(get_current_key),
):
    agent_id   = str(key_record["agent_id"])
    api_key_id = str(key_record["id"])
    tier       = payload.tier
    price      = {"basic": 10.00, "pro": 25.00}.get(tier, 10.00)

    if payload.provider == "stripe":
        result = await initiate_stripe_checkout(
            agent_id=agent_id,
            api_key_id=api_key_id,
            tier=tier,
            email=payload.email,
        )
        return {"provider": "stripe", "tier": tier, "price_gbp": price, **result}

    elif payload.provider == "coinbase":
        result = await initiate_crypto_payment(
            agent_id=agent_id,
            api_key_id=api_key_id,
            tier=tier,
        )
        return {"provider": "coinbase", "tier": tier, "price_gbp": price, **result}

    else:
        raise HTTPException(status_code=400, detail="Provider must be 'stripe' or 'coinbase'")


@router.get("/billing-portal")
async def billing_portal(key_record=Depends(get_current_key)):
    try:
        url = await get_billing_portal_url(str(key_record["agent_id"]))
        return {"portal_url": url}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/status")
async def payment_status(key_record=Depends(get_current_key)):
    from app.db.client import database
    sub = await database.fetch_one(
        """SELECT tier, status, price_gbp, provider,
                  current_period_end, cancelled_at
           FROM subscriptions
           WHERE api_key_id = :id
           ORDER BY created_at DESC LIMIT 1""",
        {"id": str(key_record["id"])}
    )

    return {
        "tier": key_record["tier"],
        "is_active": key_record["is_active"],
        "subscription": dict(sub) if sub else None,
        "trial_expires_at": key_record.get("trial_expires_at"),
        "upgrade_url": "https://agentdb.ai/pricing",
    }
