"""
AgentDB Knowledge Scraper — Reporter
Sends a plain-text email summary of the scraper run via Gmail SMTP.
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _get_config() -> Optional[Dict]:
    """
    Read required environment variables for email sending.

    Returns:
        Config dict or None if any required variable is missing.
    """
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    report_email = os.environ.get("REPORT_EMAIL", "").strip()

    missing = []
    if not gmail_user:
        missing.append("GMAIL_USER")
    if not gmail_password:
        missing.append("GMAIL_APP_PASSWORD")
    if not report_email:
        missing.append("REPORT_EMAIL")

    if missing:
        logger.error("Cannot send report — missing env vars: %s", ", ".join(missing))
        return None

    return {
        "gmail_user": gmail_user,
        "gmail_password": gmail_password,
        "report_email": report_email,
    }


def _build_report_body(results: List[Dict[str, Any]]) -> str:
    """
    Render the plain-text email body from the list of run results.

    Each result dict should contain:
        - source_name (str)
        - content_type (str): "youtube" or "blog"
        - success (bool)
        - title (str, optional): title of ingested content
        - url (str, optional)
        - error (str, optional): failure reason
    """
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

    # --- Successes ---
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

    # --- Failures ---
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
    lines.append("This report was generated automatically by AgentDB Scraper.")
    return "\n".join(lines)


def send_report(results: List[Dict[str, Any]]) -> bool:
    """
    Send the run report email via Gmail SMTP.

    Args:
        results: List of result dicts — one per source processed.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    config = _get_config()
    if config is None:
        return False

    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    succeeded_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    subject = (
        f"AgentDB Scraper Report {now_date} — "
        f"{succeeded_count}/{total_count} ingested"
    )

    body = _build_report_body(results)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config["gmail_user"]
    msg["To"] = config["report_email"]

    logger.info(
        "Sending report to %s via %s",
        config["report_email"],
        config["gmail_user"],
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config["gmail_user"], config["gmail_password"])
            server.sendmail(
                config["gmail_user"],
                [config["report_email"]],
                msg.as_string(),
            )
        logger.info("Report email sent successfully.")
        return True

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "Gmail authentication failed. Check GMAIL_USER and GMAIL_APP_PASSWORD. "
            "Note: GMAIL_APP_PASSWORD must be an App Password, not your account password. "
            "Error: %s",
            exc,
        )
        return False
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending report: %s", exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error sending report: %s", exc)
        return False
