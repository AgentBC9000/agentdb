#!/usr/bin/env python3
"""
Keepalive ping for Supabase free tier.
Runs SELECT 1 to prevent the project from auto-pausing after 1 week of inactivity.
Called by .github/workflows/keepalive.yml every 6 hours.
"""

import asyncio
import os
import re
import sys
from urllib.parse import urlparse, unquote


async def ping():
    try:
        import asyncpg
    except ImportError:
        print("asyncpg not installed", flush=True)
        sys.exit(1)

    raw_url = (
        os.environ.get("AGENTDB_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()

    if not raw_url:
        print("ERROR: AGENTDB_DATABASE_URL is not set", flush=True)
        sys.exit(1)

    # Strip asyncpg dialect prefix if present
    url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)
    # Strip query params (e.g. ?sslmode=require) — asyncpg handles ssl separately
    url = re.sub(r"\?.*$", "", url)

    # Parse URL components individually so special characters in the password
    # (e.g. @, /, #) don't break asyncpg's own URL parser.
    parsed = urlparse(url)
    try:
        port = parsed.port or 5432
    except ValueError:
        print(
            f"ERROR: AGENTDB_DATABASE_URL has a malformed port — "
            f"got {parsed._hostinfo!r}. "
            f"Expected format: postgresql://postgres:PASSWORD@db.HOST.supabase.co:5432/postgres",
            flush=True,
        )
        sys.exit(1)

    if not parsed.hostname:
        print(
            "ERROR: AGENTDB_DATABASE_URL is missing the hostname. "
            "Expected format: postgresql://postgres:PASSWORD@db.HOST.supabase.co:5432/postgres",
            flush=True,
        )
        sys.exit(1)

    connect_kwargs = dict(
        host=parsed.hostname,
        port=port,
        user=parsed.username or "postgres",
        password=unquote(parsed.password) if parsed.password else None,
        database=(parsed.path or "/postgres").lstrip("/") or "postgres",
        ssl="require",
        timeout=15,
    )

    try:
        conn = await asyncpg.connect(**connect_kwargs)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"Supabase ping OK — SELECT 1 = {result}", flush=True)
    except Exception as exc:
        print(f"ERROR: Supabase ping failed: {exc}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(ping())
