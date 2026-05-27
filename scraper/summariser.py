"""
AgentDB Knowledge Scraper — Summariser
Uses DeepSeek via the OpenAI-compatible SDK for low-cost sequential summarisation.
No batch API required — DeepSeek Flash is cheap enough to call sequentially.
"""

import json
import logging
import os
import re
from typing import Optional

import openai

logger = logging.getLogger(__name__)


class CreditExhaustedError(Exception):
    """Raised when DeepSeek rejects a call due to exhausted credits/billing."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "deepseek-v4-flash"
MAX_INPUT_CHARS = 80_000   # ~20k tokens; truncate beyond this to stay within context
MIN_TEXT_CHARS = 500        # below this, content is likely a stub or paywall — skip

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

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
- "guests": array of strings — for podcasts only, list any notable guests mentioned. \
  Empty array for non-podcast content.

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client() -> openai.OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set")
    if len(api_key) < 20:
        raise ValueError(f"DEEPSEEK_API_KEY looks invalid (length {len(api_key)})")
    return openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    logger.warning("Content truncated from %d to %d chars", len(text), max_chars)
    return truncated + "\n\n[... content truncated ...]"


def _parse_json_response(content: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from the model response.
    With json_object mode enabled this should rarely be needed, but kept as fallback.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip()).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    logger.error("Failed to parse JSON from model response:\n%s", content[:500])
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

    kp = data.get("key_points", [])
    if isinstance(kp, list):
        result["key_points"] = [str(p).strip() for p in kp if p]

    tags = data.get("tags", [])
    if isinstance(tags, list):
        result["tags"] = [str(t).lower().strip() for t in tags if t][:6]

    try:
        conf = float(data.get("confidence", 0.5))
        result["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        result["confidence"] = 0.5

    return result


def _check_credit_error(exc: openai.APIStatusError) -> None:
    """Raise CreditExhaustedError if the API error indicates a billing problem."""
    msg = str(getattr(exc, "message", str(exc))).lower()
    if exc.status_code in (400, 402, 429) and any(
        kw in msg for kw in ("credit", "billing", "balance", "quota", "insufficient")
    ):
        raise CreditExhaustedError(
            f"DeepSeek credits exhausted (status {exc.status_code}): {exc.message}"
        ) from exc


def _build_user_message(title: str, text: str, content_type: str, source_name: str, category: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        source_name=source_name,
        category=category,
        content_type=content_type,
        title=title,
        text=_truncate(text),
    )


# ---------------------------------------------------------------------------
# Primary summarise function — sequential, one call per item
# ---------------------------------------------------------------------------

def summarise(
    title: str,
    text: str,
    content_type: str,
    source_name: str,
    category: str,
) -> Optional[dict]:
    """
    Send a single item to DeepSeek and return a structured knowledge dict.

    Returns None on failure. Raises CreditExhaustedError on billing issues.
    """
    if not text or not text.strip():
        logger.warning("Empty text passed to summariser for '%s'", title)
        return None

    user_message = _build_user_message(title, text, content_type, source_name, category)

    try:
        client = _get_client()
    except ValueError as exc:
        logger.error("%s", exc)
        return None

    try:
        logger.debug("Calling DeepSeek API (model=%s)", MODEL)
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )
    except openai.AuthenticationError as exc:
        logger.error("DeepSeek API auth failed: %s", exc)
        return None
    except openai.APIConnectionError as exc:
        logger.error("Connection error calling DeepSeek API: %s", exc)
        return None
    except openai.RateLimitError as exc:
        logger.error("Rate limit exceeded calling DeepSeek API: %s", exc)
        return None
    except openai.APIStatusError as exc:
        _check_credit_error(exc)
        logger.error("DeepSeek API error (status %s): %s", exc.status_code, exc.message)
        return None
    except Exception as exc:
        logger.error("Unexpected error calling DeepSeek API (%s): %s", type(exc).__name__, exc)
        return None

    raw_content = response.choices[0].message.content if response.choices else ""
    if not raw_content:
        logger.error("DeepSeek returned empty content for '%s'", title)
        return None

    parsed = _parse_json_response(raw_content)
    if parsed is None:
        return None

    result = _validate_result(parsed)
    guests = parsed.get("guests", [])
    result["guests"] = [str(g).strip() for g in guests if g] if isinstance(guests, list) else []
    result["source_name"] = source_name
    result["category"] = category
    result["content_type"] = content_type

    # Token usage
    usage = getattr(response, "usage", None)
    if usage:
        result["_input_tokens"] = getattr(usage, "prompt_tokens", None)
        result["_output_tokens"] = getattr(usage, "completion_tokens", None)

    logger.info(
        "Summarised '%s' — confidence=%.2f tags=%s in=%s out=%s tokens",
        result["title"],
        result["confidence"],
        result["tags"],
        result.get("_input_tokens", "?"),
        result.get("_output_tokens", "?"),
    )
    return result
