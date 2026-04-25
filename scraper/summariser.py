"""
AgentDB Knowledge Scraper — Summariser
Uses the Anthropic Message Batches API to compress raw content into structured
knowledge at 50% of standard per-token cost.

Sequential summarise() is retained for local testing.
"""

import logging
import os
import re
import time
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)


class CreditExhaustedError(Exception):
    """Raised when the Anthropic API rejects a call due to exhausted credits/billing."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-5"
MAX_INPUT_CHARS = 80_000   # ~20k tokens; truncate beyond this to stay within context
MIN_TEXT_CHARS = 500        # below this, content is likely a stub or paywall — skip Claude
BATCH_POLL_INTERVAL = 30    # seconds between batch status checks
BATCH_TIMEOUT = 1800        # 30 minutes max wait for batch completion

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

def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    if len(api_key) < 20:
        raise ValueError(f"ANTHROPIC_API_KEY looks invalid (length {len(api_key)})")
    return anthropic.Anthropic(api_key=api_key)


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
    cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip()).strip()

    try:
        import json
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                import json
                return json.loads(match.group(0))
            except Exception:
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


def _check_credit_error(exc: anthropic.APIStatusError) -> None:
    """Raise CreditExhaustedError if the API error indicates a billing problem."""
    msg = str(exc.message).lower()
    if exc.status_code in (400, 402, 429) and any(
        kw in msg for kw in ("credit", "billing", "balance", "quota", "insufficient")
    ):
        raise CreditExhaustedError(
            f"Anthropic credits exhausted (status {exc.status_code}): {exc.message}"
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
# Batch API  (primary path — 50% cost vs sequential)
# ---------------------------------------------------------------------------

def build_batch_request(
    custom_id: str,
    title: str,
    text: str,
    content_type: str,
    source_name: str,
    category: str,
) -> dict:
    """
    Build a single MessageBatch request dict ready to include in a batch submission.

    Args:
        custom_id: Unique identifier for this request (echoed back in results).
        title: Article or episode title.
        text: Raw scraped text (will be truncated if needed).
        content_type: ``"article"``, ``"podcast"``, or ``"youtube_rss"``.
        source_name: Human-readable source name.
        category: Source category slug.

    Returns:
        Dict with ``custom_id`` and ``params`` keys.
    """
    return {
        "custom_id": custom_id,
        "params": {
            "model": MODEL,
            "max_tokens": 2048,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": _build_user_message(title, text, content_type, source_name, category)}
            ],
        },
    }


def submit_batch(requests: list[dict]) -> str:
    """
    Submit a list of batch request dicts to the Anthropic Message Batches API.

    Args:
        requests: List of dicts produced by :func:`build_batch_request`.

    Returns:
        The batch ID string.

    Raises:
        CreditExhaustedError: If the API rejects due to billing issues.
        anthropic.APIError: For other API-level failures.
    """
    try:
        client = _get_client()
        batch = client.messages.batches.create(requests=requests)
        logger.info("Batch submitted — id=%s, requests=%d", batch.id, len(requests))
        return batch.id
    except anthropic.APIStatusError as exc:
        _check_credit_error(exc)
        logger.error("Batch submission failed (status %s): %s", exc.status_code, exc.message)
        raise


def poll_batch(batch_id: str) -> dict[str, Optional[dict]]:
    """
    Poll the Anthropic batch until it completes, then return parsed results.

    Args:
        batch_id: ID returned by :func:`submit_batch`.

    Returns:
        Dict mapping ``custom_id`` → parsed knowledge dict (or None on failure).

    Raises:
        TimeoutError: If the batch does not complete within BATCH_TIMEOUT seconds.
    """
    client = _get_client()
    elapsed = 0

    while elapsed < BATCH_TIMEOUT:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        logger.info(
            "Batch %s — status=%s | processing=%d succeeded=%d errored=%d expired=%d",
            batch_id,
            batch.processing_status,
            counts.processing,
            counts.succeeded,
            counts.errored,
            counts.expired,
        )
        if batch.processing_status == "ended":
            break
        time.sleep(BATCH_POLL_INTERVAL)
        elapsed += BATCH_POLL_INTERVAL
    else:
        raise TimeoutError(
            f"Batch {batch_id} did not complete within {BATCH_TIMEOUT}s — check Anthropic console"
        )

    results: dict[str, Optional[dict]] = {}
    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type == "succeeded":
            raw = result.result.message.content[0].text if result.result.message.content else ""
            parsed = _parse_json_response(raw)
            if parsed:
                validated = _validate_result(parsed)
                guests = parsed.get("guests", [])
                validated["guests"] = (
                    [str(g).strip() for g in guests if g]
                    if isinstance(guests, list)
                    else []
                )
                # Capture token usage from the API response
                usage = getattr(result.result.message, "usage", None)
                if usage:
                    validated["_input_tokens"] = getattr(usage, "input_tokens", None)
                    validated["_output_tokens"] = getattr(usage, "output_tokens", None)

                results[cid] = validated
                logger.info(
                    "Batch item %s — confidence=%.2f tags=%s in=%s out=%s tokens",
                    cid,
                    validated["confidence"],
                    validated["tags"],
                    validated.get("_input_tokens", "?"),
                    validated.get("_output_tokens", "?"),
                )
            else:
                logger.error("Failed to parse JSON for batch item %s", cid)
                results[cid] = None
        else:
            logger.error("Batch item %s result type=%s", cid, result.result.type)
            results[cid] = None

    return results


# ---------------------------------------------------------------------------
# Sequential summarise()  — retained for local testing / fallback
# ---------------------------------------------------------------------------

def summarise(
    title: str,
    text: str,
    content_type: str,
    source_name: str,
    category: str,
) -> Optional[dict]:
    """
    Send a single item to Claude and return a structured knowledge dict.
    Use the batch path (submit_batch / poll_batch) for production runs.
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
        logger.debug("Calling Claude API (model=%s)", MODEL)
        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.AuthenticationError as exc:
        logger.error("Claude API auth failed: %s", exc)
        return None
    except anthropic.APIConnectionError as exc:
        logger.error("Connection error calling Claude API: %s", exc)
        return None
    except anthropic.RateLimitError as exc:
        logger.error("Rate limit exceeded calling Claude API: %s", exc)
        return None
    except anthropic.APIStatusError as exc:
        _check_credit_error(exc)
        logger.error("Claude API error (status %s): %s", exc.status_code, exc.message)
        return None
    except Exception as exc:
        logger.error("Unexpected error calling Claude API (%s): %s", type(exc).__name__, exc)
        return None

    raw_content = message.content[0].text if message.content else ""
    if not raw_content:
        logger.error("Claude returned empty content for '%s'", title)
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

    logger.info(
        "Summarised '%s' — confidence=%.2f, tags=%s",
        result["title"], result["confidence"], result["tags"],
    )
    return result
