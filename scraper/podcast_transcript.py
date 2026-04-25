"""
AgentDB — Podcast Transcript Fetcher (Phase 1)

Checks RSS entries for <podcast:transcript> tags (Podcasting 2.0 spec) and
downloads + parses the transcript into clean plain text ready for the summariser.

Supported formats:
  text/plain        — speaker-labelled dialogue (Transistor, etc.)
  application/json  — Podcast Index JSON segment format
  text/srt          — SubRip subtitles
  text/vtt          — WebVTT subtitles

Detection order (in podcast_scraper.py):
  1. podcast:transcript tag in RSS entry   ← this module
  2. Scrape transcript from episode page   ← existing CSS selector logic
  3. Fall back to show notes
"""

import json
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AgentDB-Scraper/1.0; +https://agentdb.dev/scraper)"
    )
}

# Minimum chars to consider a transcript usable
MIN_TRANSCRIPT_CHARS = 1_000


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def find_transcript_url(entry: dict) -> Optional[tuple[str, str]]:
    """
    Look for a <podcast:transcript> URL in a feedparser entry dict.

    feedparser maps the Podcasting 2.0 namespace tag to
    ``entry["podcast_transcript"]`` as a dict with ``url`` and ``type`` keys.

    Args:
        entry: A single feedparser entry dict.

    Returns:
        ``(url, content_type)`` tuple, or ``None`` if no transcript found.
    """
    # Primary: feedparser-parsed podcast:transcript attribute
    t = entry.get("podcast_transcript")
    if isinstance(t, dict) and t.get("url"):
        return t["url"], t.get("type", "text/plain")
    if isinstance(t, list):
        for item in t:
            if isinstance(item, dict) and item.get("url"):
                return item["url"], item.get("type", "text/plain")

    # Fallback: scan entry links for transcript-type rels
    for link in entry.get("links", []):
        rel = link.get("rel", "")
        ctype = link.get("type", "")
        href = link.get("href", "")
        if not href:
            continue
        if (
            rel == "transcript"
            or "transcript" in ctype
            or ctype in ("text/srt", "text/vtt", "application/json")
        ):
            return href, ctype or "text/plain"

    # Fallback: any entry key that looks like a transcript URL
    for key, val in entry.items():
        if "transcript" not in key.lower():
            continue
        if isinstance(val, str) and val.startswith("http"):
            return val, "text/plain"
        if isinstance(val, dict) and val.get("href", "").startswith("http"):
            return val["href"], val.get("type", "text/plain")

    return None


# ---------------------------------------------------------------------------
# Fetching + parsing
# ---------------------------------------------------------------------------

def fetch_transcript(url: str, content_type: str = "text/plain") -> Optional[str]:
    """
    Download a transcript file and return clean plain text.

    Args:
        url: Direct URL to the transcript file.
        content_type: MIME type hint used when the server doesn't set one.

    Returns:
        Clean plain text string, or ``None`` on failure.
    """
    logger.info("Fetching transcript: %s (declared type=%s)", url, content_type)
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Could not fetch transcript %s: %s", url, exc)
        return None

    raw = resp.text
    actual_type = resp.headers.get("content-type", "").split(";")[0].strip()
    effective_type = actual_type or content_type

    logger.info("Transcript downloaded: %d chars (content-type=%s)", len(raw), effective_type)

    if "json" in effective_type:
        text = _parse_json(raw)
    elif "srt" in effective_type or content_type == "text/srt":
        text = _parse_srt(raw)
    elif "vtt" in effective_type or content_type == "text/vtt":
        text = _parse_vtt(raw)
    else:
        # Plain text or unknown — strip any residual HTML
        text = BeautifulSoup(raw, "html.parser").get_text(separator="\n", strip=True)

    if not text or len(text) < MIN_TRANSCRIPT_CHARS:
        logger.warning(
            "Transcript too short after parsing (%d chars) — discarding",
            len(text) if text else 0,
        )
        return None

    logger.info("Transcript parsed: %d chars", len(text))
    return text


# ---------------------------------------------------------------------------
# Format parsers
# ---------------------------------------------------------------------------

def _parse_json(raw: str) -> Optional[str]:
    """
    Parse Podcast Index JSON transcript format.

    Spec: https://github.com/Podcastindex-org/podcast-namespace/blob/main/transcripts/transcripts.md

    Expected shape::

        {
          "version": "1.0.0",
          "segments": [
            {"startTime": 0, "endTime": 5.5, "speaker": "Ben", "body": "Hello..."},
            ...
          ]
        }
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("JSON transcript parse failed: %s", exc)
        return None

    segments = data.get("segments") or (data if isinstance(data, list) else [])
    if not segments:
        logger.warning("No segments in JSON transcript")
        return None

    lines: list[str] = []
    current_speaker: Optional[str] = None

    for seg in segments:
        if not isinstance(seg, dict):
            continue
        body = (
            seg.get("body") or seg.get("text") or seg.get("words") or ""
        ).strip()
        if not body:
            continue
        speaker = (seg.get("speaker") or "").strip()
        if speaker and speaker != current_speaker:
            current_speaker = speaker
            lines.append(f"\n{speaker}: {body}")
        else:
            lines.append(body)

    return "\n".join(lines).strip() or None


def _parse_srt(raw: str) -> str:
    """Strip SRT sequence numbers and timestamps, return dialogue text."""
    # Remove sequence-number lines
    text = re.sub(r"^\d+\s*$", "", raw, flags=re.MULTILINE)
    # Remove timestamp lines  (00:00:00,000 --> 00:00:05,500)
    text = re.sub(
        r"\d{1,2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,\.]\d{3}[^\n]*",
        "",
        text,
    )
    # Strip inline HTML tags (<i>, <b>, speaker cues, etc.)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " ".join(lines)


def _parse_vtt(raw: str) -> str:
    """Strip WebVTT headers, cue identifiers and timestamps, return text."""
    # Remove WEBVTT header
    text = re.sub(r"^WEBVTT[^\n]*\n", "", raw, count=1)
    # Remove NOTE blocks
    text = re.sub(r"NOTE\b[^\n]*\n(?:[^\n]*\n)*", "", text)
    # Remove timestamp lines  (00:00.000 --> 00:05.500 or HH:MM:SS.mmm variant)
    text = re.sub(
        r"(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3}\s*-->\s*(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3}[^\n]*",
        "",
        text,
    )
    # Strip VTT cue tags
    text = re.sub(r"<[^>]+>", "", text)
    # Strip standalone cue identifier lines (digits or simple labels)
    text = re.sub(r"^\w[\w-]*\s*$", "", text, flags=re.MULTILINE)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " ".join(lines)
