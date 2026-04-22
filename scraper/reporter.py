"""
AgentDB Knowledge Scraper — Reporter
Sends a plain-text email summary of the scraper run via Resend HTTP API.

Required env vars:
    RESEND_API_KEY   — from resend.com (free tier, 3k emails/month)
    REPORT_EMAIL     — recipient address
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
FROM_ADDRESS = "AgentDB Scraper <onboarding@resend.dev>"


def _get_config() -> Optional[Dict]:
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    report_email = os.environ.get("REPORT_EMAIL", "").strip()

    missing = []
    if not resend_api_key:
        missing.append("RESEND_API_KEY")
    if not report_email:
        missing.append("REPORT_EMAIL")

    if missing:
        logger.error("Cannot send report — missing env vars: %s", ", ".join(missing))
        return None

    return {"resend_api_key": resend_api_key, "report_email": report_email}


def _build_report_body(results: List[Dict[str, Any]], abort_reason: Optional[str] = None) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(results)
    succeeded = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    lines = [
        "AgentDB Knowledge Scraper — Run Report",
        "=" * 50,
        f"Run completed at: {now_utc}",
        f"Total sources processed: {total}",
        f"Successfully ingested:   {len(succeeded)}",
        f"Failed:                  {len(failed)}",
        "",
    ]

    if abort_reason:
        lines.insert(3, "")
        lines.insert(3, f"⚠️  RUN ABORTED EARLY: {abort_reason}")
        lines.insert(3, "")


    if succeeded:
        lines.append("INGESTED")
        lines.append("-" * 50)
        for r in succeeded:
            source = r.get("source_name", "Unknown")
            ctype = r.get("content_type", "")
            title = r.get("title", "(no title)")
            url = r.get("url", "")
            tags = ", ".join(r.get("tags", []))
            confidence = r.get("confidence")

            lines.append(f"  [{ctype}] {source}")
            lines.append(f"    Title:      {title}")
            if url:
                lines.append(f"    URL:        {url}")
            if tags:
                lines.append(f"    Tags:       {tags}")
            if confidence is not None:
                lines.append(f"    Confidence: {confidence:.2f}")
            lines.append("")

    if failed:
        lines.append("FAILED")
        lines.append("-" * 50)
        for r in failed:
            source = r.get("source_name", "Unknown")
            ctype = r.get("content_type", "")
            error = r.get("error", "Unknown error")
            lines.append(f"  [{ctype}] {source}")
            lines.append(f"    Reason: {error}")
            lines.append("")

    lines.append("=" * 50)
    lines.append("AgentDB Scraper — automated report")
    return "\n".join(lines)


def send_report(results: List[Dict[str, Any]], abort_reason: Optional[str] = None) -> bool:
    config = _get_config()
    if config is None:
        return False

    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    succeeded_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    subject = (
        f"⚠️ AgentDB Scraper {now_date} — ABORTED (credits exhausted)"
        if abort_reason
        else f"AgentDB Scraper {now_date} — {succeeded_count}/{total_count} ingested"
    )
    body = _build_report_body(results, abort_reason=abort_reason)

    logger.info("Sending report to %s via Resend API", config["report_email"])

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {config['resend_api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_ADDRESS,
                "to": [config["report_email"]],
                "subject": subject,
                "text": body,
            },
            timeout=15,
        )
        if response.is_success:
            logger.info("Report email sent successfully (Resend id: %s)", response.json().get("id"))
            return True
        else:
            logger.error("Resend API error %s: %s", response.status_code, response.text[:300])
            return False
    except Exception as exc:
        logger.error("Unexpected error sending report via Resend: %s", exc)
        return False
