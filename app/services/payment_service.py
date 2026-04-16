from app.db.client import database
from app.services.stripe_service import (
    create_stripe_customer,
    create_checkout_session,
    create_billing_portal_session,
)
from app.services.coinbase_service import create_crypto_charge


async def get_or_create_stripe_customer(agent_id: str, email: str = None) -> str:
    row = await database.fetch_one(
        "SELECT stripe_customer_id FROM agents WHERE id = :id",
        {"id": agent_id}
    )

    if row and row["stripe_customer_id"]:
        return row["stripe_customer_id"]

    customer_id = await create_stripe_customer(agent_id, email)

    await database.execute(
        "UPDATE agents SET stripe_customer_id = :cid WHERE id = :id",
        {"cid": customer_id, "id": agent_id}
    )

    return customer_id


async def initiate_stripe_checkout(
    agent_id: str,
    api_key_id: str,
    tier: str = "basic",
    email: str = None,
) -> dict:
    customer_id = await get_or_create_stripe_customer(agent_id, email)

    session = await create_checkout_session(
        agent_id=agent_id,
        api_key_id=api_key_id,
        stripe_customer_id=customer_id,
        tier=tier,
    )

    return {
        "provider": "stripe",
        "checkout_url": session["checkout_url"],
        "session_id": session["session_id"],
        "message": "Visit checkout_url to complete your subscription.",
    }


async def initiate_crypto_payment(
    agent_id: str,
    api_key_id: str,
    tier: str = "basic",
) -> dict:
    charge = await create_crypto_charge(
        agent_id=agent_id,
        api_key_id=api_key_id,
        tier=tier,
    )

    return {
        "provider": "coinbase",
        "hosted_url": charge["hosted_url"],
        "charge_code": charge["charge_code"],
        "addresses": charge["addresses"],
        "accepted_currencies": charge["accepted_currencies"],
        "expires_at": charge["expires_at"],
        "message": "Send payment to one of the addresses or visit hosted_url.",
    }


async def activate_subscription(
    agent_id: str,
    api_key_id: str,
    tier: str,
    provider: str,
    provider_sub_id: str,
    period_start,
    period_end,
) -> None:
    price = {"basic": 10.00, "pro": 25.00}.get(tier, 10.00)

    await database.execute(
        """UPDATE api_keys
           SET tier = :tier, is_active = true, trial_expires_at = NULL,
               subscription_id = :sub_id
           WHERE id = :id""",
        {"tier": tier, "sub_id": provider_sub_id, "id": api_key_id}
    )

    await database.execute(
        """INSERT INTO subscriptions
               (agent_id, api_key_id, provider, provider_sub_id, tier,
                status, price_gbp, current_period_start, current_period_end)
           VALUES
               (:agent_id, :api_key_id, :provider, :provider_sub_id, :tier,
                'active', :price_gbp, :period_start, :period_end)
           ON CONFLICT (provider_sub_id)
           DO UPDATE SET
               status = 'active',
               current_period_start = EXCLUDED.current_period_start,
               current_period_end = EXCLUDED.current_period_end,
               updated_at = NOW()""",
        {
            "agent_id": agent_id,
            "api_key_id": api_key_id,
            "provider": provider,
            "provider_sub_id": provider_sub_id,
            "tier": tier,
            "price_gbp": price,
            "period_start": period_start,
            "period_end": period_end,
        }
    )


async def deactivate_subscription(provider_sub_id: str) -> None:
    await database.execute(
        """UPDATE subscriptions
           SET status = 'cancelled', cancelled_at = NOW(), updated_at = NOW()
           WHERE provider_sub_id = :sub_id""",
        {"sub_id": provider_sub_id}
    )

    await database.execute(
        """UPDATE api_keys
           SET tier = 'trial', is_active = false
           WHERE subscription_id = :sub_id""",
        {"sub_id": provider_sub_id}
    )


async def get_billing_portal_url(agent_id: str) -> str:
    row = await database.fetch_one(
        "SELECT stripe_customer_id FROM agents WHERE id = :id",
        {"id": agent_id}
    )

    if not row or not row["stripe_customer_id"]:
        raise ValueError("No Stripe customer found for this agent.")

    return await create_billing_portal_session(row["stripe_customer_id"])
