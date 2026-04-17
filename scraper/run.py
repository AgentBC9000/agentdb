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
from typing import Any

from blog_scraper import scrape_blog_source
from ingest import ingest_item
from reporter import send_report
from sources import BLOG_SOURCES, YOUTUBE_SOURCES
from summariser import summarise
from youtube_scraper import scrape_youtube_source

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


def _process_youtube_source(source: dict) -> dict[str, Any]:
    """
    Scrape → summarise → ingest one YouTube source.

    Returns a result dict suitable for the email report.
    """
    name = source["name"]
    channel_id = source["channel_id"]
    category = source["category"]

    result: dict[str, Any] = {
        "source_name": name,
        "content_type": "youtube",
        "success": False,
    }

    # 1. Scrape
    logger.info("[YouTube] Processing: %s", name)
    try:
        scraped = scrape_youtube_source(channel_id, name)
    except Exception as exc:
        logger.error("[YouTube] Unhandled error scraping %s: %s", name, exc)
        result["error"] = f"Scrape exception: {exc}"
        return result

    if scraped is None:
        result["error"] = "No transcript available or video not found"
        logger.warning("[YouTube] Skipping %s — no data", name)
        return result

    # 2. Summarise
    try:
        knowledge = summarise(
            title=scraped["title"],
            text=scraped["transcript"],
            content_type="youtube_transcript",
            source_name=name,
            category=category,
        )
    except Exception as exc:
        logger.error("[YouTube] Unhandled error summarising %s: %s", name, exc)
        result["error"] = f"Summarise exception: {exc}"
        return result

    if knowledge is None:
        result["error"] = "Claude summarisation returned no result"
        logger.warning("[YouTube] Skipping %s — summarisation failed", name)
        return result

    # Attach scrape metadata so ingest and report can use it
    knowledge["url"] = scraped["url"]
    knowledge["video_id"] = scraped["video_id"]

    # 3. Ingest
    try:
        ok = ingest_item(knowledge)
    except Exception as exc:
        logger.error("[YouTube] Unhandled error ingesting %s: %s", name, exc)
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
            content_type="blog_article",
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    logger.info("=" * 60)
    logger.info("AgentDB Knowledge Scraper — starting run")
    logger.info(
        "Sources: %d YouTube channels, %d blogs",
        len(YOUTUBE_SOURCES),
        len(BLOG_SOURCES),
    )
    logger.info("=" * 60)

    all_results: list[dict[str, Any]] = []

    # --- YouTube ---
    for source in YOUTUBE_SOURCES:
        result = _process_youtube_source(source)
        all_results.append(result)
        status = "OK" if result["success"] else f"FAIL ({result.get('error', '?')})"
        logger.info("[YouTube] %s → %s", source["name"], status)

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
