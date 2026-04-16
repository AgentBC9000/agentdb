import httpx
import hmac
import hashlib
import json
from app.core.config import settings

COINBASE_API_URL = "https://api.commerce.coinbase.com"

HEADERS = {
    "X-CC-Api-Key": settings.COINBASE_COMMERCE_API_KEY,
    "X-CC-Version": "2018-03-22",
    "Content-Type": "application/json",
}


async def create_crypto_charge(
    agent_id: str,
    api_key_id: str,
    tier: str = "basic",
) -> dict:
    price = {"basic": "10.00", "pro": "25.00"}.get(tier, "10.00")

    payload = {
        "name": f"AgentDB {tier.capitalize()} — Weekly",
        "description": f"AgentDB {tier.capitalize()} subscription.",
        "pricing_type": "fixed_price",
        "local_price": {"amount": price, "currency": "GBP"},
        "metadata": {
            "agent_id": agent_id,
            "api_key_id": api_key_id,
            "tier": tier,
        },
        "redirect_url": "https://agentdb.ai/success",
        "cancel_url": "https://agentdb.ai/pricing",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COINBASE_API_URL}/charges",
            json=payload,
            headers=HEADERS,
        )
        response.raise_for_status()
        data = response.json()["data"]

    return {
        "charge_id": data["id"],
        "charge_code": data["code"],
        "hosted_url": data["hosted_url"],
        "expires_at": data["expires_at"],
        "accepted_currencies": list(data["addresses"].keys()),
        "addresses": data["addresses"],
    }


async def verify_webhook(payload: bytes, signature: str) -> dict:
    expected_sig = hmac.new(
        settings.COINBASE_COMMERCE_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if expected_sig != signature:
        raise ValueError("Invalid webhook signature")

    return json.loads(payload)
