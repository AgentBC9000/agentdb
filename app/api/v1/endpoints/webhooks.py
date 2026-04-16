from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from datetime import datetime
import stripe

from app.core.config import settings
from app.services.payment_service import activate_subscription, deactivate_subscription

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        meta = data.get("metadata", {})
        agent_id   = meta.get("agent_id")
        api_key_id = meta.get("api_key_id")
        tier       = meta.get("tier", "basic")
        sub_id     = data.get("subscription")

        if agent_id and api_key_id and sub_id:
            sub = stripe.Subscription.retrieve(sub_id)
            await activate_subscription(
                agent_id=agent_id,
                api_key_id=api_key_id,
                tier=tier,
                provider="stripe",
                provider_sub_id=sub_id,
                period_start=datetime.fromtimestamp(sub["current_period_start"]),
                period_end=datetime.fromtimestamp(sub["current_period_end"]),
            )

    elif event_type == "invoice.payment_succeeded":
        sub_id = data.get("subscription")
        if sub_id:
            sub = stripe.Subscription.retrieve(sub_id)
            meta = sub.get("metadata", {})
            agent_id   = meta.get("agent_id")
            api_key_id = meta.get("api_key_id")
            tier       = meta.get("tier", "basic")

            if agent_id and api_key_id:
                await activate_subscription(
                    agent_id=agent_id,
                    api_key_id=api_key_id,
                    tier=tier,
                    provider="stripe",
                    provider_sub_id=sub_id,
                    period_start=datetime.fromtimestamp(sub["current_period_start"]),
                    period_end=datetime.fromtimestamp(sub["current_period_end"]),
                )

    elif event_type == "customer.subscription.deleted":
        sub_id = data.get("id")
        if sub_id:
            await deactivate_subscription(sub_id)

    elif event_type == "invoice.payment_failed":
        sub_id = data.get("subscription")
        if sub_id:
            from app.db.client import database
            await database.execute(
                "UPDATE subscriptions SET status = 'past_due', updated_at = NOW() WHERE provider_sub_id = :sub_id",
                {"sub_id": sub_id}
            )

    return {"received": True}


@router.post("/coinbase")
async def coinbase_webhook(
    request: Request,
    x_cc_webhook_signature: Optional[str] = Header(None, alias="x-cc-webhook-signature"),
):
    payload = await request.body()

    try:
        from app.services.coinbase_service import verify_webhook
        event = await verify_webhook(payload, x_cc_webhook_signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Coinbase signature")

    event_type = event.get("event", {}).get("type")
    charge     = event.get("event", {}).get("data", {})
    meta       = charge.get("metadata", {})

    agent_id   = meta.get("agent_id")
    api_key_id = meta.get("api_key_id")
    tier       = meta.get("tier", "basic")
    charge_id  = charge.get("id")

    if event_type in ("charge:confirmed", "charge:resolved"):
        if agent_id and api_key_id:
            from datetime import timedelta
            now = datetime.utcnow()
            await activate_subscription(
                agent_id=agent_id,
                api_key_id=api_key_id,
                tier=tier,
                provider="coinbase",
                provider_sub_id=charge_id,
                period_start=now,
                period_end=now + timedelta(weeks=1),
            )

    return {"received": True}
