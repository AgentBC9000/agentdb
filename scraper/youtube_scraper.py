"""
AgentDB Knowledge Scraper — YouTube Scraper
Fetches the latest video from a YouTube channel via RSS and retrieves its transcript.
"""

import logging
from typing import Optional
from xml.etree import ElementTree

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)

RSS_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"
YOUTUBE_NS = "http://www.w3.org/2005/Atom"
MEDIA_NS = "http://search.yahoo.com/mrss/"
YT_NS = "http://www.youtube.com/xml/schemas/2015"

# Preferred transcript languages in priority order
TRANSCRIPT_LANGUAGES = ["en", "en-US", "en-GB", "en-CA", "en-AU"]


def get_latest_video(channel_id: str) -> Optional[dict]:
    """
    Fetch the YouTube RSS feed for a channel and return metadata for the latest video.

    Args:
        channel_id: YouTube channel ID string.

    Returns:
        Dict with keys ``video_id`` and ``title``, or None on failure.
    """
    url = RSS_FEED_URL.format(channel_id=channel_id)
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("HTTP error fetching RSS feed for channel %s: %s", channel_id, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error fetching RSS feed for channel %s: %s", channel_id, exc)
        return None

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError as exc:
        logger.error("Failed to parse RSS XML for channel %s: %s", channel_id, exc)
        return None

    # The first <entry> in the Atom feed is the most recent video
    entry = root.find(f"{{{YOUTUBE_NS}}}entry")
    if entry is None:
        logger.warning("No entries found in RSS feed for channel %s", channel_id)
        return None

    video_id_el = entry.find(f"{{{YT_NS}}}videoId")
    title_el = entry.find(f"{{{YOUTUBE_NS}}}title")

    if video_id_el is None or title_el is None:
        logger.warning("Missing videoId or title in RSS feed for channel %s", channel_id)
        return None

    return {
        "video_id": video_id_el.text.strip(),
        "title": title_el.text.strip(),
    }


def get_transcript(video_id: str) -> Optional[str]:
    """
    Retrieve the full transcript text for a YouTube video.

    Args:
        video_id: YouTube video ID string.

    Returns:
        Concatenated transcript text, or None if unavailable.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try preferred English variants first, then fall back to auto-generated
        transcript = None
        try:
            transcript = transcript_list.find_transcript(TRANSCRIPT_LANGUAGES)
        except NoTranscriptFound:
            # Fall back to any auto-generated transcript
            try:
                transcript = transcript_list.find_generated_transcript(TRANSCRIPT_LANGUAGES)
            except NoTranscriptFound:
                # Last resort: grab whatever is available and translate if needed
                try:
                    available = list(transcript_list)
                    if available:
                        transcript = available[0]
                        if transcript.language_code not in ["en", "en-US", "en-GB"]:
                            transcript = transcript.translate("en")
                except Exception as exc:
                    logger.warning(
                        "Could not find or translate any transcript for video %s: %s",
                        video_id,
                        exc,
                    )
                    return None

        if transcript is None:
            return None

        segments = transcript.fetch()
        text = " ".join(seg["text"].strip() for seg in segments if seg.get("text"))
        return text if text else None

    except TranscriptsDisabled:
        logger.info("Transcripts disabled for video %s", video_id)
        return None
    except VideoUnavailable:
        logger.info("Video %s is unavailable", video_id)
        return None
    except Exception as exc:
        logger.error("Unexpected error fetching transcript for video %s: %s", video_id, exc)
        return None


def scrape_youtube_source(channel_id: str, source_name: str) -> Optional[dict]:
    """
    High-level helper: fetch latest video metadata and transcript for a channel.

    Args:
        channel_id: YouTube channel ID string.
        source_name: Human-readable source name for logging.

    Returns:
        Dict with keys ``video_id``, ``title``, ``transcript``, ``url``, or None on failure.
    """
    logger.info("Fetching latest video for %s (channel: %s)", source_name, channel_id)

    video_meta = get_latest_video(channel_id)
    if video_meta is None:
        logger.warning("Could not retrieve latest video for %s", source_name)
        return None

    video_id = video_meta["video_id"]
    title = video_meta["title"]
    url = VIDEO_URL.format(video_id=video_id)

    logger.info("Found video '%s' (%s) — fetching transcript", title, video_id)

    transcript = get_transcript(video_id)
    if transcript is None:
        logger.warning("No transcript available for '%s' (%s)", title, video_id)
        return None

    logger.info(
        "Retrieved transcript for '%s' (%d chars)", title, len(transcript)
    )

    return {
        "video_id": video_id,
        "title": title,
        "transcript": transcript,
        "url": url,
    }
