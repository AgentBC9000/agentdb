#!/usr/bin/env python3
"""
AgentDB + LlamaIndex — ReAct Research Agent
=============================================
A LlamaIndex ReActAgent with AgentDB registered as FunctionTools.
The agent reasons step-by-step, fetching knowledge as needed.

Usage:
    pip install llama-index llama-index-llms-anthropic httpx

    ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx \\
        python 07_llamaindex_agent.py "What's happening in quantum computing?"

    # Or with OpenAI:
    pip install llama-index-llms-openai
    OPENAI_API_KEY=sk-xxx AGENTDB_API_KEY=adb_xxx \\
        python 07_llamaindex_agent.py "Summarise today's market news"

Get an AgentDB key (free):
    curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \\
         -H "Content-Type: application/json" -d '{}'
"""

import os
import sys
from typing import Optional

try:
    import httpx
    from llama_index.core.agent import ReActAgent
    from llama_index.core.tools import FunctionTool
except ImportError:
    print("Install dependencies:  pip install llama-index llama-index-llms-anthropic httpx")
    sys.exit(1)

AGENTDB_URL   = "https://agentdb-production-9ba0.up.railway.app"
AGENTDB_KEY   = os.environ.get("AGENTDB_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY", "")


# ── LLM setup ─────────────────────────────────────────────────────────────────

def get_llm():
    if ANTHROPIC_KEY:
        try:
            from llama_index.llms.anthropic import Anthropic
            return Anthropic(model="claude-opus-4-5", api_key=ANTHROPIC_KEY)
        except ImportError:
            print("Install:  pip install llama-index-llms-anthropic")
            sys.exit(1)
    elif OPENAI_KEY:
        try:
            from llama_index.llms.openai import OpenAI
            return OpenAI(model="gpt-4o", api_key=OPENAI_KEY)
        except ImportError:
            print("Install:  pip install llama-index-llms-openai")
            sys.exit(1)
    else:
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        sys.exit(1)


# ── AgentDB tool functions ────────────────────────────────────────────────────

def get_latest_knowledge(limit: int = 8, tags: Optional[str] = None) -> str:
    """
    Fetch the latest knowledge items from AgentDB — a curated real-time
    knowledge base updated Mon/Wed/Fri covering markets, technology, science,
    philosophy, and current events. Use to get fresh context on recent events.

    Args:
        limit: Number of items to return (1-20, default 8)
        tags: Comma-separated tags to filter by, e.g. 'ai,markets'

    Returns:
        Formatted knowledge items with summaries and key points
    """
    params = {"limit": limit}
    if tags:
        params["tags"] = tags

    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{AGENTDB_URL}/v1/knowledge/latest",
            headers={"X-API-Key": AGENTDB_KEY},
            params=params,
        )
        resp.raise_for_status()

    return _format_items(resp.json()["items"])


def search_knowledge(query: str, limit: int = 5) -> str:
    """
    Semantic search across AgentDB knowledge base. Use when you need
    specific information on a topic rather than just the latest items.
    Returns the most semantically relevant results.

    Args:
        query: Natural language search query
        limit: Number of results to return (1-10, default 5)

    Returns:
        Formatted knowledge items most relevant to the query
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{AGENTDB_URL}/v1/knowledge/search",
            headers={"X-API-Key": AGENTDB_KEY},
            params={"q": query, "limit": limit},
        )
        if resp.status_code == 403:
            return "Semantic search requires Pro. Upgrade at https://agentdb.dev/pricing"
        resp.raise_for_status()

    return _format_items(resp.json()["items"])


def _format_items(items: list) -> str:
    if not items:
        return "No items found."
    parts = []
    for item in items:
        body = item.get("body") or {}
        lines = [f"## {item['title']}"]
        source = body.get("source_name", "")
        pub = str(item.get("published_at", ""))[:10]
        if source or pub:
            lines.append(f"Source: {source}  Date: {pub}")
        if item.get("tags"):
            lines.append(f"Tags: {', '.join(item['tags'])}")
        if item.get("summary"):
            lines.append(f"\n{item['summary']}")
        kp = body.get("key_points", [])
        if kp:
            lines.append("\nKey points:")
            for k in kp[:3]:
                lines.append(f"  • {k}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


# ── Agent setup ───────────────────────────────────────────────────────────────

def build_agent() -> ReActAgent:
    tools = [
        FunctionTool.from_defaults(fn=get_latest_knowledge),
        FunctionTool.from_defaults(fn=search_knowledge),
    ]

    llm = get_llm()

    return ReActAgent.from_tools(
        tools,
        llm=llm,
        verbose=True,
        system_prompt=(
            "You are a research assistant with access to AgentDB, a curated "
            "real-time knowledge base updated Mon/Wed/Fri. Always check AgentDB "
            "before answering questions about current events, markets, technology, "
            "or science. Cite your sources and be concise."
        ),
        max_iterations=10,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not AGENTDB_KEY:
        print("Set AGENTDB_API_KEY. Get a free key:")
        print("  curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \\")
        print("       -H 'Content-Type: application/json' -d '{}'")
        sys.exit(1)

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Question: ").strip()
    print(f"\nQuestion: {question}\n{'─' * 60}\n")

    agent = build_agent()
    response = agent.chat(question)

    print(f"\n{'─' * 60}")
    print(str(response))
    print("─" * 60)
    print("Powered by AgentDB — agentdb.dev")


if __name__ == "__main__":
    main()
