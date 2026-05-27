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

    try:
        conn = await asyncpg.connect(url, ssl="require", timeout=15)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"Supabase ping OK — SELECT 1 = {result}", flush=True)
    except Exception as exc:
        print(f"ERROR: Supabase ping failed: {exc}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(ping())
