"""
AgentDB Knowledge Scraper — Main Entry Point
Runs Mon/Wed/Fri at 07:00 UTC (configure via Railway cron: "0 7 * * 1,3,5").

Pipeline
--------
Phase 1  Scrape all sources (RSS → HTML → clean text)
Phase 2  Filter stubs  (text < MIN_TEXT_CHARS → skip, no Claude call)
Phase 3  Submit one Anthropic Message Batch (50 % cost vs sequential calls)
Phase 4  Poll until batch completes
Phase 5  Ingest results into AgentDB
Phase 6  Send email report

Required environment variables:
    ANTHROPIC_API_KEY       — Anthropic API key for Claude summarisation
    AGENTDB_API_URL         — Base URL of the AgentDB API
    AGENTDB_ADMIN_SECRET    — Admin bearer token for /v1/knowledge/ingest
    RESEND_API_KEY          — Resend HTTP API key for email reports
    REPORT_EMAIL            — Recipient address for the run report
"""

import logging
import re
import sys
from typing import Any

from blog_scraper import scrape_blog_source
from ingest import ingest_item
from podcast_scraper import scrape_podcast_source
from reporter import send_report
from sources import BLOG_SOURCES, PODCAST_SOURCES, YOUTUBE_RSS_SOURCES
from summariser import (
    MIN_TEXT_CHARS,
    CreditExhaustedError,
    build_batch_request,
    poll_batch,
    submit_batch,
)

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
# Helpers
# ---------------------------------------------------------------------------

def _make_custom_id(prefix: str, name: str) -> str:
    """
    Build a batch custom_id that satisfies Anthropic's pattern ^[a-zA-Z0-9_-]{1,64}$.
    Spaces → underscores, all other non-alphanumeric chars stripped, truncated to 64.
    """
    raw = f"{prefix}__{name.replace(' ', '_')}"
    return re.sub(r"[^a-zA-Z0-9_-]", "", raw)[:64]


# ---------------------------------------------------------------------------
# Phase 1 helpers — scrape each source type
# ---------------------------------------------------------------------------

def _scrape_podcasts() -> tuple[list[dict], list[dict[str, Any]]]:
    """
    Scrape all podcast sources.

    Returns:
        (scraped_items, failed_results)
        scraped_items — items ready for batch submission
        failed_results — items that failed scraping (for the report)
    """
    scraped, failed = [], []

    for source in PODCAST_SOURCES:
        name = source["name"]
        logger.info("[Podcast] Scraping: %s", name)

        try:
            data = scrape_podcast_source(source)
        except Exception as exc:
            logger.error("[Podcast] Scrape exception for %s: %s", name, exc)
            failed.append({"source_name": name, "content_type": "podcast",
                           "success": False, "error": f"Scrape exception: {exc}"})
            continue

        if data is None:
            failed.append({"source_name": name, "content_type": "podcast",
                           "success": False, "error": "No episode content found"})
            continue

        text = data.get("text", "")
        if len(text) < MIN_TEXT_CHARS:
            logger.warning("[Podcast] Skipping %s — text too short (%d chars, stub/paywall)", name, len(text))
            failed.append({"source_name": name, "content_type": "podcast",
                           "success": False, "error": f"Content too short ({len(text)} chars) — stub or paywall"})
            continue

        custom_id = _make_custom_id("podcast", name)
        scraped.append({
            "custom_id": custom_id,
            "scraped": data,
            "source_name": name,
            "category": source["category"],
            "content_type": "podcast",
            "hosts": source.get("hosts", []),
        })
        logger.info("[Podcast] %s scraped OK (%d chars)", name, len(text))

    return scraped, failed


def _scrape_blogs() -> tuple[list[dict], list[dict[str, Any]]]:
    """
    Scrape all blog sources.

    Returns:
        (scraped_items, failed_results)
    """
    scraped, failed = [], []

    for source in BLOG_SOURCES:
        name = source["name"]
        logger.info("[Blog] Scraping: %s", name)

        try:
            data = scrape_blog_source(source["rss_url"], name)
        except Exception as exc:
            logger.error("[Blog] Scrape exception for %s: %s", name, exc)
            failed.append({"source_name": name, "content_type": "article",
                           "success": False, "error": f"Scrape exception: {exc}"})
            continue

        if data is None:
            failed.append({"source_name": name, "content_type": "article",
                           "success": False, "error": "Could not fetch or parse article"})
            continue

        text = data.get("text", "")
        if len(text) < MIN_TEXT_CHARS:
            logger.warning("[Blog] Skipping %s — text too short (%d chars, stub/paywall)", name, len(text))
            failed.append({"source_name": name, "content_type": "article",
                           "success": False, "error": f"Content too short ({len(text)} chars) — stub or paywall"})
            continue

        custom_id = _make_custom_id("blog", name)
        scraped.append({
            "custom_id": custom_id,
            "scraped": data,
            "source_name": name,
            "category": source["category"],
            "content_type": "article",
        })
        logger.info("[Blog] %s scraped OK (%d chars)", name, len(text))

    return scraped, failed


def _scrape_youtube() -> tuple[list[dict], list[dict[str, Any]]]:
    """
    Scrape all YouTube RSS sources (description-only, no transcripts).

    Returns:
        (scraped_items, failed_results)
    """
    scraped, failed = [], []

    for source in YOUTUBE_RSS_SOURCES:
        name = source["name"]
        logger.info("[YouTube] Scraping: %s", name)

        try:
            data = scrape_blog_source(source["rss_url"], name)
        except Exception as exc:
            logger.error("[YouTube] Scrape exception for %s: %s", name, exc)
            failed.append({"source_name": name, "content_type": "youtube_rss",
                           "success": False, "error": f"Scrape exception: {exc}"})
            continue

        if data is None:
            failed.append({"source_name": name, "content_type": "youtube_rss",
                           "success": False, "error": "Could not fetch RSS description"})
            continue

        text = data.get("text", "")
        if len(text) < MIN_TEXT_CHARS:
            logger.warning("[YouTube] Skipping %s — text too short (%d chars)", name, len(text))
            failed.append({"source_name": name, "content_type": "youtube_rss",
                           "success": False, "error": f"Content too short ({len(text)} chars)"})
            continue

        custom_id = _make_custom_id("youtube", name)
        scraped.append({
            "custom_id": custom_id,
            "scraped": data,
            "source_name": name,
            "category": source["category"],
            "content_type": "youtube_rss",
        })
        logger.info("[YouTube] %s scraped OK (%d chars)", name, len(text))

    return scraped, failed


# ---------------------------------------------------------------------------
# Phase 5 helper — ingest one summarised item
# ---------------------------------------------------------------------------

def _ingest_item(item: dict, knowledge: dict) -> dict[str, Any]:
    """
    Attach metadata to a knowledge dict and POST it to AgentDB.

    Returns:
        A result dict suitable for the email report.
    """
    content_type = item["content_type"]
    name = item["source_name"]
    scraped = item["scraped"]

    knowledge["url"] = scraped.get("url", "")
    knowledge["source_name"] = name
    knowledge["category"] = item["category"]
    knowledge["content_type"] = content_type

    # Podcasts carry extra metadata in a nested body dict
    if content_type == "podcast":
        knowledge["body"] = {
            "hosts": item.get("hosts", []),
            "guests": knowledge.pop("guests", []),
            "audio_url": scraped.get("audio_url", ""),
            "source_name": name,
        }

    try:
        ok = ingest_item(knowledge)
    except Exception as exc:
        logger.error("[Ingest] Exception for %s: %s", name, exc)
        return {"source_name": name, "content_type": content_type,
                "success": False, "error": f"Ingest exception: {exc}"}

    if ok:
        return {
            "source_name": name,
            "content_type": content_type,
            "success": True,
            "title": knowledge["title"],
            "url": scraped.get("url", ""),
            "tags": knowledge.get("tags", []),
            "confidence": knowledge.get("confidence"),
        }
    return {"source_name": name, "content_type": content_type,
            "success": False, "error": "AgentDB ingest rejected the item"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("AgentDB Knowledge Scraper — starting run")
    logger.info(
        "Sources: %d blogs, %d podcasts, %d YouTube RSS",
        len(BLOG_SOURCES), len(PODCAST_SOURCES), len(YOUTUBE_RSS_SOURCES),
    )
    logger.info("=" * 60)

    # ── Phase 1: Scrape all sources ──────────────────────────────────────────
    logger.info("Phase 1 — Scraping sources …")
    pod_scraped, pod_failed = _scrape_podcasts()
    blog_scraped, blog_failed = _scrape_blogs()
    yt_scraped, yt_failed = _scrape_youtube()

    all_scraped = pod_scraped + blog_scraped + yt_scraped
    pre_batch_failures = pod_failed + blog_failed + yt_failed

    logger.info(
        "Phase 1 complete — %d items to summarise, %d skipped (stubs/failures)",
        len(all_scraped), len(pre_batch_failures),
    )

    if not all_scraped:
        logger.error("No items passed scraping — aborting run")
        send_report(pre_batch_failures)
        sys.exit(1)

    # ── Phase 2/3: Build batch requests and submit ───────────────────────────
    logger.info("Phase 2 — Building and submitting Anthropic batch (%d items) …", len(all_scraped))

    batch_requests = [
        build_batch_request(
            custom_id=item["custom_id"],
            title=item["scraped"]["title"],
            text=item["scraped"]["text"],
            content_type=item["content_type"],
            source_name=item["source_name"],
            category=item["category"],
        )
        for item in all_scraped
    ]

    try:
        batch_id = submit_batch(batch_requests)
    except CreditExhaustedError as exc:
        logger.error("ABORTING — credits exhausted before batch submission: %s", exc)
        send_report(pre_batch_failures, abort_reason=str(exc))
        sys.exit(0)  # graceful abort
    except Exception as exc:
        logger.error("Batch submission failed: %s", exc)
        send_report(pre_batch_failures, abort_reason=f"Batch submission error: {exc}")
        sys.exit(1)

    # ── Phase 4: Poll for batch completion ───────────────────────────────────
    logger.info("Phase 3 — Polling batch %s …", batch_id)

    try:
        batch_results = poll_batch(batch_id)
    except TimeoutError as exc:
        logger.error("Batch timed out: %s", exc)
        send_report(pre_batch_failures, abort_reason=str(exc))
        sys.exit(1)
    except Exception as exc:
        logger.error("Unexpected error polling batch: %s", exc)
        send_report(pre_batch_failures, abort_reason=f"Batch poll error: {exc}")
        sys.exit(1)

    # ── Phase 5: Ingest results ──────────────────────────────────────────────
    logger.info("Phase 4 — Ingesting %d summarised items …", len(batch_results))

    ingest_results: list[dict[str, Any]] = []
    for item in all_scraped:
        cid = item["custom_id"]
        knowledge = batch_results.get(cid)

        if knowledge is None:
            ingest_results.append({
                "source_name": item["source_name"],
                "content_type": item["content_type"],
                "success": False,
                "error": "Claude summarisation returned no result",
            })
            continue

        result = _ingest_item(item, knowledge)
        ingest_results.append(result)
        status = "OK" if result["success"] else f"FAIL ({result.get('error', '?')})"
        logger.info("[%s] %s → %s", item["content_type"].upper(), item["source_name"], status)

    # ── Phase 6: Report ──────────────────────────────────────────────────────
    all_results = pre_batch_failures + ingest_results
    succeeded = sum(1 for r in all_results if r["success"])
    failed = len(all_results) - succeeded

    logger.info("=" * 60)
    logger.info("Run complete — %d/%d ingested, %d failed", succeeded, len(all_results), failed)
    logger.info("=" * 60)

    logger.info("Sending email report …")
    if send_report(all_results):
        logger.info("Report sent.")
    else:
        logger.warning("Report could not be sent.")

    if succeeded == 0 and len(all_results) > 0:
        logger.error("All sources failed — exiting with code 1")
        sys.exit(1)


if __name__ == "__main__":
    main()
