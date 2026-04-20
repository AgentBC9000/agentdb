"""
AgentDB Knowledge Scraper — Main Entry Point
Runs Mon/Wed/Fri at 07:00 UTC (configure via Railway cron: "0 7 * * 1,3,5").

Required environment variables:
    ANTHROPIC_API_KEY       — Anthropic API key for Claude summarisation
    AGENTDB_API_URL         — Base URL of the AgentDB API
                              e.g. https://agentdb-production-9ba0.up.railway.app
    AGENTDB_ADMIN_SECRET    — Admin bearer token for AgentDB /v1/knowledge/ingest
    GMAIL_USER              — Gmail address used to send reports (agentbc9000@gmail.com)
    GMAIL_APP_PASSWORD      — Gmail App Password (NOT the account password)
                              Generate at: https://myaccount.google.com/apppasswords
    REPORT_EMAIL            — Recipient address for the run report (agentbc9000@gmail.com)
"""

import logging
import sys
from typing import Any, Dict, List

from blog_scraper import scrape_blog_source
from ingest import ingest_item
from podcast_scraper import scrape_podcast_source
from reporter import send_report
from sources import BLOG_SOURCES, PODCAST_SOURCES
from summariser import summarise

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
logger = logging.getLogger("agentdb.scraper")


# ---------------------------------------------------------------------------
# Per-source processing helpers
# ---------------------------------------------------------------------------


def _process_blog_source(source: dict) -> dict[str, Any]:
    """
    Scrape → summarise → ingest one blog source.

    Returns a result dict suitable for the email report.
    """
    name = source["name"]
    rss_url = source["rss_url"]
    category = source["category"]

    result: dict[str, Any] = {
        "source_name": name,
        "content_type": "blog",
        "success": False,
    }

    # 1. Scrape
    logger.info("[Blog] Processing: %s", name)
    try:
        scraped = scrape_blog_source(rss_url, name)
    except Exception as exc:
        logger.error("[Blog] Unhandled error scraping %s: %s", name, exc)
        result["error"] = f"Scrape exception: {exc}"
        return result

    if scraped is None:
        result["error"] = "Could not fetch or parse article"
        logger.warning("[Blog] Skipping %s — no data", name)
        return result

    # 2. Summarise
    try:
        knowledge = summarise(
            title=scraped["title"],
            text=scraped["text"],
            content_type="article",
            source_name=name,
            category=category,
        )
    except Exception as exc:
        logger.error("[Blog] Unhandled error summarising %s: %s", name, exc)
        result["error"] = f"Summarise exception: {exc}"
        return result

    if knowledge is None:
        result["error"] = "Claude summarisation returned no result"
        logger.warning("[Blog] Skipping %s — summarisation failed", name)
        return result

    knowledge["url"] = scraped["url"]

    # 3. Ingest
    try:
        ok = ingest_item(knowledge)
    except Exception as exc:
        logger.error("[Blog] Unhandled error ingesting %s: %s", name, exc)
        result["error"] = f"Ingest exception: {exc}"
        return result

    if not ok:
        result["error"] = "AgentDB ingest rejected the item (check logs above)"
        return result

    result.update(
        {
            "success": True,
            "title": knowledge["title"],
            "url": scraped["url"],
            "tags": knowledge.get("tags", []),
            "confidence": knowledge.get("confidence"),
        }
    )
    return result


def _process_podcast_source(source: dict) -> dict[str, Any]:
    """
    Scrape → summarise → ingest one podcast source.
    Returns a result dict suitable for the email report.
    """
    name = source["name"]
    category = source["category"]
    hosts = source.get("hosts", [])

    result: dict[str, Any] = {
        "source_name": name,
        "content_type": "podcast",
        "success": False,
    }

    # 1. Scrape
    logger.info("[Podcast] Processing: %s", name)
    try:
        scraped = scrape_podcast_source(source)
    except Exception as exc:
        logger.error("[Podcast] Unhandled error scraping %s: %s", name, exc)
        result["error"] = f"Scrape exception: {exc}"
        return result

    if scraped is None:
        result["error"] = "No episode content available"
        logger.warning("[Podcast] Skipping %s — no data", name)
        return result

    # 2. Summarise
    try:
        knowledge = summarise(
            title=scraped["title"],
            text=scraped["text"],
            content_type="podcast",
            source_name=name,
            category=category,
        )
    except Exception as exc:
        logger.error("[Podcast] Unhandled error summarising %s: %s", name, exc)
        result["error"] = f"Summarise exception: {exc}"
        return result

    if knowledge is None:
        result["error"] = "Claude summarisation returned no result"
        logger.warning("[Podcast] Skipping %s — summarisation failed", name)
        return result

    # Attach podcast-specific metadata to body
    knowledge["url"] = scraped.get("url", "")
    knowledge["body"] = knowledge.get("body") or {}
    if isinstance(knowledge["body"], dict):
        knowledge["body"]["hosts"] = hosts
        knowledge["body"]["guests"] = knowledge.pop("guests", [])
        knowledge["body"]["audio_url"] = scraped.get("audio_url", "")
        knowledge["body"]["source_name"] = name

    # 3. Ingest
    try:
        ok = ingest_item(knowledge)
    except Exception as exc:
        logger.error("[Podcast] Unhandled error ingesting %s: %s", name, exc)
        result["error"] = f"Ingest exception: {exc}"
        return result

    if not ok:
        result["error"] = "AgentDB ingest rejected the item (check logs above)"
        return result

    result.update(
        {
            "success": True,
            "title": knowledge["title"],
            "url": scraped.get("url", ""),
            "tags": knowledge.get("tags", []),
            "confidence": knowledge.get("confidence"),
        }
    )
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    logger.info("=" * 60)
    logger.info("AgentDB Knowledge Scraper — starting run")
    logger.info(
        "Sources: %d blogs, %d podcasts",
        len(BLOG_SOURCES),
        len(PODCAST_SOURCES),
    )
    logger.info("=" * 60)

    all_results: List[Dict[str, Any]] = []

    # --- Podcasts ---
    for source in PODCAST_SOURCES:
        result = _process_podcast_source(source)
        all_results.append(result)
        status = "OK" if result["success"] else f"FAIL ({result.get('error', '?')})"
        logger.info("[Podcast] %s → %s", source["name"], status)

    # --- Blogs ---
    for source in BLOG_SOURCES:
        result = _process_blog_source(source)
        all_results.append(result)
        status = "OK" if result["success"] else f"FAIL ({result.get('error', '?')})"
        logger.info("[Blog] %s → %s", source["name"], status)

    # --- Summary ---
    succeeded = sum(1 for r in all_results if r["success"])
    failed = len(all_results) - succeeded
    logger.info("=" * 60)
    logger.info(
        "Run complete — %d/%d ingested, %d failed",
        succeeded,
        len(all_results),
        failed,
    )
    logger.info("=" * 60)

    # --- Report ---
    logger.info("Sending email report …")
    report_sent = send_report(all_results)
    if report_sent:
        logger.info("Report sent successfully.")
    else:
        logger.warning("Report could not be sent (see errors above).")

    # Exit with non-zero code if everything failed (useful for Railway health checks)
    if succeeded == 0 and len(all_results) > 0:
        logger.error("All sources failed — exiting with code 1")
        sys.exit(1)


if __name__ == "__main__":
    main()
