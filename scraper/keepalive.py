#!/usr/bin/env python3
"""
Keepalive ping for Supabase free tier.
Hits the REST API to prevent the project from auto-pausing after 1 week of inactivity.
Uses HTTPS (port 443) — more reliable than direct Postgres from cloud runners.
Called by .github/workflows/keepalive.yml every 6 hours.

Required env vars:
    SUPABASE_URL         — e.g. https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY — service role key (or anon key with SELECT policy)
"""

import os
import sys

import httpx


def ping():
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

    missing = []
    if not url:
        missing.append("SUPABASE_URL")
    if not key:
        missing.append("SUPABASE_SERVICE_KEY")
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}", flush=True)
        sys.exit(1)

    endpoint = f"{url}/rest/v1/knowledge?select=id&limit=1"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    try:
        resp = httpx.get(endpoint, headers=headers, timeout=15)
        if resp.is_success:
            print(f"Supabase ping OK — GET /rest/v1/knowledge returned HTTP {resp.status_code}", flush=True)
        else:
            print(f"ERROR: Supabase ping returned HTTP {resp.status_code}: {resp.text[:200]}", flush=True)
            sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Supabase ping failed: {exc}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    ping()
