#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.0.0", "httpx>=0.25.0"]
# ///
"""
AgentDB MCP Server
Exposes the AgentDB knowledge base as tools for Claude and other MCP-compatible agents.

Quick start (requires uv — https://docs.astral.sh/uv/getting-started/installation/):
    AGENTDB_API_KEY=your-key uv run /path/to/agentdb/mcp/server.py

Claude Desktop / Claude Code — add to ~/.claude.json or project .mcp.json:
    {
      "mcpServers": {
        "agentdb": {
          "command": "uv",
          "args": ["run", "/absolute/path/to/agentdb/mcp/server.py"],
          "env": { "AGENTDB_API_KEY": "your-key-here" }
        }
      }
    }

Get an API key at https://agentdb.dev
"""

import asyncio
import os

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── Config ────────────────────────────────────────────────────────────────────

API_URL = os.environ.get(
    "AGENTDB_API_URL",
    "https://agentdb-production-9ba0.up.railway.app",
).rstrip("/")
API_KEY = os.environ.get("AGENTDB_API_KEY", "")

# ── Server ────────────────────────────────────────────────────────────────────

app = Server("agentdb")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_latest_knowledge",
            description=(
                "Fetch the latest knowledge items from AgentDB — a curated, "
                "real-time knowledge base updated Mon/Wed/Fri with summaries "
                "from YouTube channels, blogs, and research sources covering "
                "markets, technology, science, philosophy, and current events. "
                "Use this to get fresh context before answering questions or "
                "when the user asks about recent developments."
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
                            "Examples: 'ai,machine-learning', 'market-news', "
                            "'quantum-mechanics', 'startups'"
                        ),
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Filter by content type",
                        "enum": ["article", "video", "research", "data"],
                    },
                },
            },
        ),
        types.Tool(
            name="search_knowledge",
            description=(
                "Search AgentDB using a natural language query. Returns the most "
                "semantically relevant knowledge items. Use this when you need "
                "specific information on a topic rather than just the latest items."
                "\n\nRequires a Pro API key."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
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
    if not API_KEY:
        return [types.TextContent(
            type="text",
            text="Error: AGENTDB_API_KEY environment variable is not set.",
        )]

    headers = {"X-API-Key": API_KEY}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if name == "get_latest_knowledge":
                params: dict = {"limit": arguments.get("limit", 10)}
                if arguments.get("tags"):
                    params["tags"] = arguments["tags"]
                if arguments.get("content_type"):
                    params["content_type"] = arguments["content_type"]

                resp = await client.get(
                    f"{API_URL}/v1/knowledge/latest",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
                return [types.TextContent(type="text", text=_format_items(data["items"]))]

            elif name == "search_knowledge":
                resp = await client.get(
                    f"{API_URL}/v1/knowledge/search",
                    headers=headers,
                    params={
                        "q": arguments["query"],
                        "limit": arguments.get("limit", 5),
                    },
                )
                if resp.status_code == 403:
                    return [types.TextContent(
                        type="text",
                        text="Semantic search requires an AgentDB Pro key. Get one at https://agentdb.dev/pricing",
                    )]
                resp.raise_for_status()
                data = resp.json()
                return [types.TextContent(type="text", text=_format_items(data["items"]))]

    except httpx.HTTPStatusError as exc:
        return [types.TextContent(
            type="text",
            text=f"AgentDB API error (HTTP {exc.response.status_code}): {exc.response.text[:200]}",
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

        lines.append(f"\nID: {item['id']}")
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


def main_sync() -> None:
    """Entry point for the agentdb-mcp script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
