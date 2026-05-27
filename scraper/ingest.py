"""
AgentDB Knowledge Scraper — Ingest
Writes summarised knowledge items directly to Supabase via the PostgREST API.
No FastAPI layer required.
"""

import json
import logging
import os
import uuid
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30  # seconds


def _get_config() -> Optional[tuple]:
    """
    Read Supabase credentials from environment.

    Returns:
        Tuple of (rest_url, service_key), or None if either is missing.
    """
    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

    if not supabase_url:
        logger.error("SUPABASE_URL environment variable is not set.")
        return None
    if not service_key:
        logger.error("SUPABASE_SERVICE_KEY environment variable is not set.")
        return None

    rest_url = f"{supabase_url}/rest/v1/knowledge"
    return rest_url, service_key


def _build_payload(item: dict) -> dict:
    """Map a summarised knowledge item to the knowledge table row."""
    body = {
        "key_points": item.get("key_points", []),
        "source_name": item.get("source_name", ""),
        "category": item.get("category", ""),
    }

    token_meta = item.pop("_token_meta", None) or {}
    if token_meta:
        body.update(token_meta)

    # Podcast-specific body fields passed through from run.py
    if item.get("body"):
        body.update(item["body"])

    return {
        "id": str(uuid.uuid4()),
        "title": item.get("title", ""),
        "content_type": item.get("content_type", "article"),
        "summary": item.get("summary", ""),
        "body": body,
        "tags": item.get("tags", []),
        "source_url": item.get("url") or None,
        "confidence": item.get("confidence", 0.5),
        "relevance_score": item.get("confidence", 0.5),
    }


def ingest_item(item: dict) -> bool:
    """
    Insert a knowledge item directly into Supabase via the PostgREST API.

    Args:
        item: Dict produced by summariser.summarise() with url/category/content_type attached.

    Returns:
        True if inserted successfully, False otherwise.
    """
    config = _get_config()
    if config is None:
        return False

    rest_url, service_key = config
    payload = _build_payload(item)

    logger.info("Ingesting '%s' → Supabase", payload["title"])

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(rest_url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.error("HTTP error ingesting '%s': %s", payload["title"], exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error ingesting '%s': %s", payload["title"], exc)
        return False

    if response.is_success:
        logger.info("Ingested '%s' (HTTP %s)", payload["title"], response.status_code)
        return True

    logger.error(
        "Supabase rejected ingest for '%s': HTTP %s — %s",
        payload["title"],
        response.status_code,
        response.text[:300],
    )
    return False
