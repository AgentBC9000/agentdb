"""
AgentDB Knowledge Scraper — Podcast Scraper
Fetches the latest episode from a podcast RSS feed.

Strategy (transcript-first, no Whisper needed for Phase 1):
  1. Parse RSS feed → get latest episode (title, date, audio URL, show notes)
  2. Fetch episode page → try to extract transcript from page HTML
  3. Fall back to show notes if no transcript found
  4. Return structured dict for the summariser

Phase 2 will add OpenAI Whisper for podcasts without web transcripts.
"""

import logging
import re
from typing import Optional
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

try:
    import feedparser
except ImportError:
    raise ImportError("Install feedparser:  pip install feedparser")

from podcast_transcript import fetch_transcript, find_transcript_url

logger = logging.getLogger(__name__)

# Minimum text length to consider usable content (show notes alone are often short)
MIN_CONTENT_CHARS = 500

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _parse_rss(rss_url: str) -> Optional[dict]:
    """Fetch and parse RSS feed, return latest episode metadata."""
    try:
        feed = feedparser.parse(rss_url)
    except Exception as exc:
        logger.error("Failed to parse RSS feed %s: %s", rss_url, exc)
        return None

    if not feed.entries:
        logger.warning("No entries in RSS feed: %s", rss_url)
        return None

    entry = feed.entries[0]

    # Get audio URL from enclosures
    audio_url = None
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("audio"):
                audio_url = enc.get("href") or enc.get("url")
                break

    # Published date
    pub_date = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            pub_date = datetime(*entry.published_parsed[:6]).isoformat()
        except Exception:
            pass

    # Show notes from entry summary/content
    show_notes = ""
    if hasattr(entry, "content") and entry.content:
        show_notes = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        show_notes = entry.summary or ""

    # Strip HTML from show notes
    if show_notes:
        soup = BeautifulSoup(show_notes, "html.parser")
        show_notes = soup.get_text(separator="\n").strip()

    return {
        "title": entry.get("title", "Untitled Episode"),
        "url": entry.get("link", ""),
        "audio_url": audio_url,
        "show_notes": show_notes,
        "published_at": pub_date,
        "podcast_name": feed.feed.get("title", ""),
        "_entry": entry,   # raw feedparser entry — used for transcript detection
    }


def _fetch_transcript_from_page(url: str, transcript_selectors: list) -> Optional[str]:
    """
    Try to extract a transcript from the episode's web page.
    Uses CSS selectors specific to each podcast's site structure.
    """
    if not url:
        return None

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Could not fetch episode page %s: %s", url, exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    for selector in transcript_selectors:
        try:
            elements = soup.select(selector)
            if elements:
                text = "\n".join(el.get_text(separator="\n").strip() for el in elements)
                if len(text) > MIN_CONTENT_CHARS:
                    logger.info("Transcript found via selector '%s' (%d chars)", selector, len(text))
                    return text
        except Exception:
            continue

    return None


def scrape_podcast_source(source: dict) -> Optional[dict]:
    """
    Main entry point. Scrape one podcast source and return content
    ready for the summariser.

    Args:
        source: Dict with keys:
            - name: Human-readable podcast name
            - rss_url: RSS feed URL
            - category: Category slug
            - transcript_selectors: List of CSS selectors to try for transcript extraction
            - hosts: List of host names (optional)

    Returns:
        Dict with title, text, url, audio_url, hosts, published_at — or None on failure.
    """
    name = source["name"]
    rss_url = source["rss_url"]
    transcript_selectors = source.get("transcript_selectors", [])
    hosts = source.get("hosts", [])

    logger.info("[Podcast] Fetching RSS: %s", name)

    # 1. Parse RSS
    episode = _parse_rss(rss_url)
    if not episode:
        logger.warning("[Podcast] No episode found for %s", name)
        return None

    logger.info("[Podcast] Latest episode: %s", episode["title"])

    # 2a. Check RSS entry for <podcast:transcript> tag (Podcasting 2.0)
    transcript = None
    raw_entry = episode.pop("_entry", {})
    transcript_ref = find_transcript_url(raw_entry)
    if transcript_ref:
        t_url, t_type = transcript_ref
        logger.info("[Podcast] RSS transcript tag found for %s: %s", name, t_url)
        transcript = fetch_transcript(t_url, t_type)
        if transcript:
            logger.info(
                "[Podcast] RSS transcript fetched for %s (%d chars)", name, len(transcript)
            )
        else:
            logger.warning("[Podcast] RSS transcript fetch failed for %s — falling back", name)

    # 2b. Try to scrape transcript from episode web page (existing CSS selector logic)
    if not transcript and transcript_selectors and episode.get("url"):
        transcript = _fetch_transcript_from_page(episode["url"], transcript_selectors)

    # 3. Build content text
    if transcript and len(transcript) > MIN_CONTENT_CHARS:
        text = transcript
        logger.info("[Podcast] Using page transcript (%d chars)", len(text))
    elif episode.get("show_notes") and len(episode["show_notes"]) > MIN_CONTENT_CHARS:
        text = episode["show_notes"]
        logger.info("[Podcast] Using show notes (%d chars)", len(text))
    else:
        # Combine what we have
        parts = []
        if episode.get("show_notes"):
            parts.append(episode["show_notes"])
        text = "\n\n".join(parts)
        if len(text) < MIN_CONTENT_CHARS:
            logger.warning(
                "[Podcast] Insufficient content for %s (%d chars) — skipping",
                name,
                len(text),
            )
            return None

    return {
        "title": episode["title"],
        "text": text,
        "url": episode["url"],
        "audio_url": episode.get("audio_url"),
        "hosts": hosts,
        "published_at": episode.get("published_at"),
        "podcast_name": episode.get("podcast_name", name),
    }
