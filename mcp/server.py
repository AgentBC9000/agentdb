#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.0.0", "httpx>=0.25.0"]
# ///
"""
AgentDB MCP Server
Exposes the AgentDB knowledge base as tools for Claude and other MCP-compatible agents.

Requires two environment variables:
  AGENTDB_SUPABASE_URL  — your Supabase project URL (e.g. https://xxxx.supabase.co)
  AGENTDB_API_KEY       — your AgentDB API key (contact agentbc9000@gmail.com)

Quick start (requires uv — https://docs.astral.sh/uv/getting-started/installation/):
  AGENTDB_SUPABASE_URL=https://xxxx.supabase.co \\
  AGENTDB_API_KEY=your-key \\
  uv run /path/to/agentdb/mcp/server.py

Claude Desktop / Claude Code — add to ~/.claude.json or project .mcp.json:
  {
    "mcpServers": {
      "agentdb": {
        "command": "uv",
        "args": ["run", "/absolute/path/to/agentdb/mcp/server.py"],
        "env": {
          "AGENTDB_SUPABASE_URL": "https://xxxx.supabase.co",
          "AGENTDB_API_KEY": "your-key-here"
        }
      }
    }
  }

Request access at https://agentdb.pages.dev
"""

import asyncio
import json
import os

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("AGENTDB_SUPABASE_URL", "").rstrip("/")
API_KEY = os.environ.get("AGENTDB_API_KEY", "")

# Columns to select — excludes the embedding vector (large, not useful to agents)
SELECT_COLS = "id,title,content_type,summary,body,tags,source_url,confidence,relevance_score,published_at"

# ── Server ────────────────────────────────────────────────────────────────────

app = Server("agentdb")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_latest_knowledge",
            description=(
                "Fetch the latest knowledge items from AgentDB — a curated knowledge "
                "base updated Mon/Wed/Fri from 41 sources covering AI/tech, startups, "
                "alternative markets, and emerging economies (Africa & Asia). Each item "
                "is an AI-generated structured summary with key points, tags, and a "
                "confidence score. Use this to give your agent fresh context before "
                "answering questions about recent developments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of items to return (1–50, default 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "tags": {
                        "type": "string",
                        "description": (
                            "Comma-separated tags to filter by. "
                            "Examples: 'ai', 'startups', 'markets', 'emerging-markets'"
                        ),
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Filter by content type: article, video, research, or data",
                        "enum": ["article", "video", "research", "data"],
                    },
                },
            },
        ),
        types.Tool(
            name="search_knowledge",
            description=(
                "Search AgentDB knowledge items by keyword. Searches titles and summaries. "
                "Use this when you need information on a specific topic rather than "
                "just the latest items."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or phrase to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (1–20, default 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if not SUPABASE_URL:
        return [types.TextContent(
            type="text",
            text="Error: AGENTDB_SUPABASE_URL environment variable is not set.",
        )]
    if not API_KEY:
        return [types.TextContent(
            type="text",
            text="Error: AGENTDB_API_KEY environment variable is not set. Request access at https://agentdb.pages.dev",
        )]

    headers = {
        "apikey": API_KEY,
        "Authorization": f"Bearer {API_KEY}",
    }
    rest_url = f"{SUPABASE_URL}/rest/v1/knowledge"

    try:
        async with httpx.AsyncClient(timeout=15) as client:

            if name == "get_latest_knowledge":
                params: dict[str, str | int] = {
                    "select": SELECT_COLS,
                    "is_active": "eq.true",
                    "order": "published_at.desc",
                    "limit": arguments.get("limit", 10),
                }
                # Tag filter — PostgREST array contains: tags=cs.{ai,startups}
                if arguments.get("tags"):
                    tag_list = ",".join(
                        t.strip() for t in arguments["tags"].split(",") if t.strip()
                    )
                    params["tags"] = f"cs.{{{tag_list}}}"
                # Content type filter
                if arguments.get("content_type"):
                    params["content_type"] = f"eq.{arguments['content_type']}"

                resp = await client.get(rest_url, headers=headers, params=params)
                resp.raise_for_status()
                items = resp.json()
                return [types.TextContent(type="text", text=_format_items(items))]

            elif name == "search_knowledge":
                query = arguments["query"].strip()
                # ilike search across title and summary
                params = {
                    "select": SELECT_COLS,
                    "is_active": "eq.true",
                    "or": f"(title.ilike.*{query}*,summary.ilike.*{query}*)",
                    "order": "published_at.desc",
                    "limit": arguments.get("limit", 5),
                }
                resp = await client.get(rest_url, headers=headers, params=params)
                resp.raise_for_status()
                items = resp.json()
                return [types.TextContent(type="text", text=_format_items(items))]

    except httpx.HTTPStatusError as exc:
        return [types.TextContent(
            type="text",
            text=f"AgentDB error (HTTP {exc.response.status_code}): {exc.response.text[:300]}",
        )]
    except httpx.HTTPError as exc:
        return [types.TextContent(type="text", text=f"Network error: {exc}")]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ── Formatting ────────────────────────────────────────────────────────────────

def _format_items(items: list) -> str:
    if not items:
        return "No items found."

    parts = []
    for item in items:
        body = item.get("body") or {}
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except Exception:
                body = {}

        key_points = body.get("key_points", [])
        source_name = body.get("source_name", "")

        lines = [f"## {item['title']}"]

        meta = []
        if source_name:
            meta.append(f"Source: {source_name}")
        if item.get("content_type"):
            meta.append(f"Type: {item['content_type']}")
        if item.get("published_at"):
            meta.append(f"Published: {str(item['published_at'])[:10]}")
        if item.get("confidence") is not None:
            meta.append(f"Confidence: {item['confidence']:.0%}")
        if meta:
            lines.append(" | ".join(meta))

        if item.get("tags"):
            lines.append(f"Tags: {', '.join(item['tags'])}")

        if item.get("summary"):
            lines.append("")
            lines.append(item["summary"])

        if key_points:
            lines.append("")
            lines.append("Key points:")
            for kp in key_points:
                lines.append(f"  • {kp}")

        if item.get("source_url"):
            lines.append(f"\nSource: {item['source_url']}")

        parts.append("\n".join(lines))

    return "\n\n---\n\n".join(parts)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
