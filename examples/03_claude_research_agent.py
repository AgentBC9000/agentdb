#!/usr/bin/env python3
"""
AgentDB + Claude — Research Agent with Tool Use
================================================
A Claude agent that autonomously decides when to query AgentDB for
fresh context, then synthesises an answer grounded in current events.

Claude uses AgentDB as a tool — it calls get_latest_knowledge and
search_knowledge exactly when it decides it needs them.

Usage:
    pip install anthropic httpx
    ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx \\
        python 03_claude_research_agent.py

    # Or pipe a question directly:
    echo "What's the latest in AI safety research?" | \\
    ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx python 03_claude_research_agent.py

Get an AgentDB key: https://agentdb-production-9ba0.up.railway.app/v1/auth/register
"""

import os
import sys
import json

try:
    import httpx
    import anthropic
except ImportError:
    print("Install dependencies:  pip install anthropic httpx")
    sys.exit(1)

AGENTDB_URL   = "https://agentdb-production-9ba0.up.railway.app"
AGENTDB_KEY   = os.environ.get("AGENTDB_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL         = "claude-opus-4-5"


# ── Tool definitions (passed to Claude) ──────────────────────────────────────

TOOLS = [
    {
        "name": "get_latest_knowledge",
        "description": (
            "Fetch the latest knowledge items from AgentDB — a curated real-time "
            "knowledge base updated Mon/Wed/Fri covering markets, technology, science, "
            "philosophy, and current events. Use this when you need recent context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of items to return (1-20)",
                    "default": 8,
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags to filter by, e.g. 'ai,markets'",
                },
                "content_type": {
                    "type": "string",
                    "enum": ["article", "video", "research", "data"],
                    "description": "Filter by content type",
                },
            },
        },
    },
    {
        "name": "search_knowledge",
        "description": (
            "Semantic search across AgentDB. Use this when you need information "
            "on a specific topic rather than just the latest items. Returns the "
            "most relevant results for your query. Requires a Pro API key."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results (1-10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
]


# ── Tool execution ────────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> str:
    """Execute an AgentDB tool call and return the result as a string."""
    headers = {"X-API-Key": AGENTDB_KEY}

    with httpx.Client(timeout=15) as client:
        if name == "get_latest_knowledge":
            params: dict = {"limit": inputs.get("limit", 8)}
            if inputs.get("tags"):
                params["tags"] = inputs["tags"]
            if inputs.get("content_type"):
                params["content_type"] = inputs["content_type"]

            resp = client.get(f"{AGENTDB_URL}/v1/knowledge/latest", headers=headers, params=params)
            resp.raise_for_status()
            items = resp.json()["items"]

        elif name == "search_knowledge":
            resp = client.get(
                f"{AGENTDB_URL}/v1/knowledge/search",
                headers=headers,
                params={"q": inputs["query"], "limit": inputs.get("limit", 5)},
            )
            if resp.status_code == 403:
                return "Semantic search requires a Pro AgentDB key. Falling back — use get_latest_knowledge with relevant tags instead."
            resp.raise_for_status()
            items = resp.json()["items"]

        else:
            return f"Unknown tool: {name}"

    # Format items for Claude
    parts = []
    for item in items:
        body       = item.get("body") or {}
        key_points = body.get("key_points", [])
        source     = body.get("source_name", "")
        pub        = str(item.get("published_at", ""))[:10]

        block = [f"## {item['title']}"]
        meta = []
        if source:
            meta.append(f"Source: {source}")
        if pub:
            meta.append(f"Date: {pub}")
        if item.get("content_type"):
            meta.append(f"Type: {item['content_type']}")
        if meta:
            block.append(" | ".join(meta))
        if item.get("tags"):
            block.append(f"Tags: {', '.join(item['tags'])}")
        if item.get("summary"):
            block.append(f"\n{item['summary']}")
        if key_points:
            block.append("\nKey points:")
            for kp in key_points:
                block.append(f"  • {kp}")
        block.append(f"\nID: {item['id']}")
        parts.append("\n".join(block))

    return "\n\n---\n\n".join(parts) if parts else "No results found."


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(question: str) -> None:
    if not AGENTDB_KEY:
        print("Set AGENTDB_API_KEY. Get a free key at https://agentdb-production-9ba0.up.railway.app/v1/auth/register")
        sys.exit(1)
    if not ANTHROPIC_KEY:
        print("Set ANTHROPIC_API_KEY.")
        sys.exit(1)

    client   = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    messages = [{"role": "user", "content": question}]

    print(f"\nQuestion: {question}\n")
    print("─" * 60)

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=(
                "You are a research assistant with access to AgentDB, a real-time "
                "curated knowledge base updated Mon/Wed/Fri. Always check AgentDB "
                "before answering questions about current events, markets, technology, "
                "science, or philosophy. Cite your sources."
            ),
            tools=TOOLS,
            messages=messages,
        )

        # Print any text content immediately
        for block in response.content:
            if hasattr(block, "text"):
                print(block.text)

        # If no tool calls, we're done
        if response.stop_reason == "end_turn":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\n[Calling AgentDB: {block.name}({json.dumps(block.input)})]")
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
                print(f"[Got {len(result.split(chr(10)))} lines of context]")

        if not tool_results:
            break

        # Append assistant response and tool results, continue loop
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})

    print()
    print("─" * 60)
    print("Powered by AgentDB — agentdb.dev")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not sys.stdin.isatty():
        question = sys.stdin.read().strip()
    elif len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        print("Enter your question (or pass it as an argument / pipe it in):")
        question = input("> ").strip()

    if not question:
        print("No question provided.")
        sys.exit(1)

    run_agent(question)


if __name__ == "__main__":
    main()
