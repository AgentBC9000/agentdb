"""
AgentDB Knowledge Scraper — Ingest
POSTs compressed knowledge items to the AgentDB /v1/knowledge/ingest endpoint.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

INGEST_PATH = "/v1/knowledge/ingest"
REQUEST_TIMEOUT = 30  # seconds


def _get_config() -> Optional[tuple]:
    """
    Read required environment variables.

    Returns:
        Tuple of (api_url, admin_secret), or None if either is missing.
    """
    api_url = os.environ.get("AGENTDB_API_URL", "").rstrip("/")
    admin_secret = os.environ.get("AGENTDB_ADMIN_SECRET", "")

    if not api_url:
        logger.error(
            "AGENTDB_API_URL environment variable is not set. "
            "Example: https://agentdb-production-9ba0.up.railway.app"
        )
        return None

    if not admin_secret:
        logger.error("AGENTDB_ADMIN_SECRET environment variable is not set.")
        return None

    return api_url, admin_secret


def _build_payload(item: dict) -> dict:
    """
    Map a summarised knowledge item to the AgentDB ingest request payload.

    Maps summariser output to the API's IngestRequest schema:
      title, content_type, summary, body, tags, source_url, confidence
    """
    # Pack extra metadata into the body dict so nothing is lost
    body = {
        "key_points": item.get("key_points", []),
        "source_name": item.get("source_name", ""),
        "category": item.get("category", ""),
    }
    if item.get("video_id"):
        body["video_id"] = item["video_id"]

    return {
        "title": item.get("title", ""),
        "content_type": item.get("content_type", "blog_article"),
        "summary": item.get("summary", ""),
        "body": body,
        "tags": item.get("tags", []),
        "source_url": item.get("url") or None,
        "confidence": item.get("confidence", 0.5),
        "relevance_score": item.get("confidence", 0.5),  # use confidence as relevance too
        "generate_embedding": False,  # no OpenAI key in scraper
    }


def ingest_item(item: dict) -> bool:
    """
    POST a knowledge item to the AgentDB ingest endpoint.

    Args:
        item: Dict produced by summariser.summarise() with optional ``url``
              and ``video_id`` fields attached by the caller.

    Returns:
        True if the item was accepted (2xx response), False otherwise.
    """
    config = _get_config()
    if config is None:
        return False

    api_url, admin_secret = config
    endpoint = api_url + INGEST_PATH
    payload = _build_payload(item)

    logger.info("Ingesting '%s' to %s", item.get("title", "<no title>"), endpoint)

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                endpoint,
                json=payload,
                params={"secret": admin_secret},
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "AgentDB-Scraper/1.0",
                },
            )
    except httpx.HTTPError as exc:
        logger.error(
            "HTTP error posting to AgentDB for '%s': %s",
            item.get("title", ""),
            exc,
        )
        return False
    except Exception as exc:
        logger.error(
            "Unexpected error posting to AgentDB for '%s': %s",
            item.get("title", ""),
            exc,
        )
        return False

    if response.is_success:
        logger.info(
            "Successfully ingested '%s' (HTTP %s)",
            item.get("title", ""),
            response.status_code,
        )
        return True

    logger.error(
        "AgentDB rejected ingest for '%s': HTTP %s — %s",
        item.get("title", ""),
        response.status_code,
        response.text[:300],
    )
    return False
