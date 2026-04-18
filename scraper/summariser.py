"""
AgentDB Knowledge Scraper — Summariser
Uses Claude to compress raw content into structured knowledge.
"""

import json
import logging
import re
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-5"
MAX_INPUT_CHARS = 80_000  # ~20k tokens; truncate beyond this to stay within context

SYSTEM_PROMPT = """\
You are a knowledge compression engine. Your job is to read raw content (video transcripts \
or article text) and extract the most valuable, durable knowledge from it.

You MUST respond with valid JSON only — no markdown fences, no preamble, no explanation. \
The JSON object must have exactly these fields:

- "title": string — a clean, descriptive title (may differ slightly from the source title)
- "summary": string — 2-3 paragraphs of compressed, information-dense prose capturing the \
  core ideas, arguments, findings, and conclusions
- "key_points": array of strings — 5-10 concrete, standalone takeaways a reader can act on \
  or remember
- "tags": array of 3-6 lowercase strings — relevant topic tags (e.g. "monetary-policy", \
  "machine-learning", "consciousness")
- "confidence": float between 0.0 and 1.0 — your confidence that the content is substantive \
  and the extraction is accurate (lower if transcript is garbled, article is paywalled/stub, \
  or content is low-signal)

Be concise but information-rich. Avoid filler phrases. Prioritise facts, data, and novel \
insights over generic observations.\
"""

USER_PROMPT_TEMPLATE = """\
Source: {source_name}
Category: {category}
Content type: {content_type}
Title: {title}

--- BEGIN CONTENT ---
{text}
--- END CONTENT ---

Compress the above into structured knowledge JSON as instructed.\
"""


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to avoid exceeding context limits, preserving the beginning."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    logger.warning("Content truncated from %d to %d chars", len(text), max_chars)
    return truncated + "\n\n[... content truncated ...]"


def _parse_json_response(content: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from Claude's response text.
    Handles cases where the model inadvertently wraps output in markdown.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to locate first { ... } block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    logger.error("Failed to parse JSON from Claude response:\n%s", content[:500])
    return None


def _validate_result(data: dict) -> dict:
    """Apply sensible defaults / coercions to the parsed result dict."""
    result = {
        "title": str(data.get("title", "Untitled")).strip(),
        "summary": str(data.get("summary", "")).strip(),
        "key_points": [],
        "tags": [],
        "confidence": 0.5,
    }

    # key_points
    kp = data.get("key_points", [])
    if isinstance(kp, list):
        result["key_points"] = [str(p).strip() for p in kp if p]

    # tags
    tags = data.get("tags", [])
    if isinstance(tags, list):
        result["tags"] = [str(t).lower().strip() for t in tags if t][:6]

    # confidence
    try:
        conf = float(data.get("confidence", 0.5))
        result["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        result["confidence"] = 0.5

    return result


def summarise(
    title: str,
    text: str,
    content_type: str,
    source_name: str,
    category: str,
) -> Optional[dict]:
    """
    Send content to Claude and return a structured knowledge dict.

    Args:
        title: Article or video title.
        text: Raw transcript or article text.
        content_type: ``"youtube_transcript"`` or ``"blog_article"``.
        source_name: Human-readable source name (e.g. ``"Bloomberg"``).
        category: Source category slug (e.g. ``"market_news"``).

    Returns:
        Dict with keys ``title``, ``summary``, ``key_points``, ``tags``,
        ``confidence``, plus metadata fields — or None on failure.
    """
    if not text or not text.strip():
        logger.warning("Empty text passed to summariser for '%s'", title)
        return None

    truncated_text = _truncate(text)

    user_message = USER_PROMPT_TEMPLATE.format(
        source_name=source_name,
        category=category,
        content_type=content_type,
        title=title,
        text=truncated_text,
    )

    try:
        client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIConnectionError as exc:
        logger.error("Connection error calling Claude API: %s", exc)
        return None
    except anthropic.RateLimitError as exc:
        logger.error("Rate limit exceeded calling Claude API: %s", exc)
        return None
    except anthropic.APIStatusError as exc:
        logger.error("Claude API error (status %s): %s", exc.status_code, exc.message)
        return None
    except Exception as exc:
        logger.error("Unexpected error calling Claude API: %s", exc)
        return None

    raw_content = message.content[0].text if message.content else ""
    if not raw_content:
        logger.error("Claude returned empty content for '%s'", title)
        return None

    parsed = _parse_json_response(raw_content)
    if parsed is None:
        return None

    result = _validate_result(parsed)

    # Attach metadata that the ingest step will need
    result["source_name"] = source_name
    result["category"] = category
    result["content_type"] = content_type

    logger.info(
        "Summarised '%s' — confidence=%.2f, tags=%s",
        result["title"],
        result["confidence"],
        result["tags"],
    )
    return result
