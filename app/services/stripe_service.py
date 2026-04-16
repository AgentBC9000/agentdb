import stripe
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_stripe_customer(agent_id: str, email: str = None) -> str:
    customer = stripe.Customer.create(
        email=email,
        metadata={"agent_id": agent_id}
    )
    return customer.id


async def create_checkout_session(
    agent_id: str,
    api_key_id: str,
    stripe_customer_id: str,
    tier: str = "basic",
    success_url: str = "https://agentdb.ai/success",
    cancel_url: str = "https://agentdb.ai/pricing",
) -> dict:
    price_id = {
        "basic": settings.STRIPE_PRICE_ID_BASIC,
        "pro":   settings.STRIPE_PRICE_ID_PRO,
    }.get(tier, settings.STRIPE_PRICE_ID_BASIC)

    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={
            "agent_id": agent_id,
            "api_key_id": api_key_id,
            "tier": tier,
        },
        subscription_data={
            "metadata": {
                "agent_id": agent_id,
                "api_key_id": api_key_id,
                "tier": tier,
            }
        }
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }


async def cancel_subscription(subscription_id: str) -> bool:
    stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True
    )
    return True


async def create_billing_portal_session(
    stripe_customer_id: str,
    return_url: str = "https://agentdb.ai/dashboard"
) -> str:
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url
