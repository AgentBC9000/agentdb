#!/usr/bin/env python3
"""
AgentDB — Daily Briefing Agent
================================
Fetches the latest knowledge items and prints a formatted briefing.
No LLM required — just AgentDB.

Usage:
    pip install httpx
    AGENTDB_API_KEY=adb_xxx python 01_daily_briefing.py

    # Filter to specific topics:
    AGENTDB_API_KEY=adb_xxx python 01_daily_briefing.py --tags ai,markets
    AGENTDB_API_KEY=adb_xxx python 01_daily_briefing.py --type video --limit 5

Get a free API key: https://agentdb-production-9ba0.up.railway.app/v1/auth/register
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from typing import Optional

try:
    import httpx
except ImportError:
    print("Install httpx first:  pip install httpx")
    sys.exit(1)

API_URL  = "https://agentdb-production-9ba0.up.railway.app"
API_KEY  = os.environ.get("AGENTDB_API_KEY", "")


def register() -> str:
    """Register for a trial key if none is set."""
    print("No AGENTDB_API_KEY found. Registering for a free trial key...")
    resp = httpx.post(f"{API_URL}/v1/auth/register", json={}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    key  = data["api_key"]
    print(f"\n  Your API key: {key}")
    print(f"  Trial expires: {data['trial_expires_at']}")
    print(f"\n  Save it:  export AGENTDB_API_KEY={key}\n")
    return key


def fetch_latest(key: str, limit: int, tags: Optional[str], content_type: Optional[str]) -> list:
    params: dict = {"limit": limit}
    if tags:
        params["tags"] = tags
    if content_type:
        params["content_type"] = content_type

    resp = httpx.get(
        f"{API_URL}/v1/knowledge/latest",
        headers={"X-API-Key": key},
        params=params,
        timeout=15,
    )
    if resp.status_code == 401:
        print("Error: invalid API key. Check your AGENTDB_API_KEY.")
        sys.exit(1)
    if resp.status_code == 402:
        print("Trial expired. Upgrade at https://agentdb.dev/pricing")
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()["items"]


def print_briefing(items: list, tags: Optional[str], content_type: Optional[str]) -> None:
    now = datetime.now(timezone.utc).strftime("%A, %B %-d %Y")

    print()
    print("=" * 60)
    print(f"  AgentDB Briefing — {now}")
    if tags:
        print(f"  Filter: tags={tags}")
    if content_type:
        print(f"  Filter: type={content_type}")
    print(f"  {len(items)} items")
    print("=" * 60)

    for i, item in enumerate(items, 1):
        body        = item.get("body") or {}
        key_points  = body.get("key_points", [])
        source_name = body.get("source_name", "")
        pub_date    = str(item.get("published_at", ""))[:10]
        ctype       = item.get("content_type", "")
        tags_list   = ", ".join(item.get("tags") or [])

        print(f"\n{i}. {item['title']}")

        meta = []
        if source_name:
            meta.append(source_name)
        if ctype:
            meta.append(ctype)
        if pub_date:
            meta.append(pub_date)
        if meta:
            print(f"   {' · '.join(meta)}")

        if tags_list:
            print(f"   [{tags_list}]")

        if item.get("summary"):
            # Wrap to 72 chars
            words, line = item["summary"].split(), ""
            print()
            for word in words:
                if len(line) + len(word) + 1 > 72:
                    print(f"   {line}")
                    line = word
                else:
                    line = f"{line} {word}".strip()
            if line:
                print(f"   {line}")

        if key_points:
            print()
            for kp in key_points[:3]:
                print(f"   • {kp[:100]}")

        print(f"\n   id: {item['id']}")
        print()

    print("=" * 60)
    print("  Powered by AgentDB — https://agentdb.dev")
    print("=" * 60)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentDB daily briefing")
    parser.add_argument("--limit", type=int, default=10, help="Number of items (default: 10)")
    parser.add_argument("--tags",  type=str, default=None, help="Comma-separated tags, e.g. ai,markets")
    parser.add_argument("--type",  type=str, default=None,
                        choices=["article", "video", "research", "data"],
                        help="Content type filter")
    args = parser.parse_args()

    key = API_KEY or register()

    print(f"\nFetching latest knowledge from AgentDB...", end="", flush=True)
    items = fetch_latest(key, limit=args.limit, tags=args.tags, content_type=args.type)
    print(f" {len(items)} items received.")

    print_briefing(items, tags=args.tags, content_type=args.type)


if __name__ == "__main__":
    main()
