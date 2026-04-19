#!/usr/bin/env python3
"""
AgentDB + AutoGen — Research Agent
====================================
An AutoGen AssistantAgent with AgentDB registered as a callable tool.
The agent autonomously decides when to fetch knowledge and synthesises
a grounded answer.

Usage:
    pip install pyautogen httpx

    ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx \\
        python 06_autogen_agent.py "What's the latest in AI safety research?"

    # Or with OpenAI:
    OPENAI_API_KEY=sk-xxx AGENTDB_API_KEY=adb_xxx \\
        python 06_autogen_agent.py "Summarise today's market news"

Get an AgentDB key (free):
    curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \\
         -H "Content-Type: application/json" -d '{}'
"""

import os
import sys
from typing import Optional, Annotated

try:
    import httpx
    import autogen
except ImportError:
    print("Install dependencies:  pip install pyautogen httpx")
    sys.exit(1)

AGENTDB_URL   = "https://agentdb-production-9ba0.up.railway.app"
AGENTDB_KEY   = os.environ.get("AGENTDB_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY", "")


# ── LLM config (Anthropic or OpenAI) ─────────────────────────────────────────

def get_llm_config():
    if ANTHROPIC_KEY:
        return {
            "config_list": [{
                "model": "claude-opus-4-5",
                "api_key": ANTHROPIC_KEY,
                "api_type": "anthropic",
            }],
            "timeout": 120,
        }
    elif OPENAI_KEY:
        return {
            "config_list": [{"model": "gpt-4o", "api_key": OPENAI_KEY}],
            "timeout": 120,
        }
    else:
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        sys.exit(1)


# ── AgentDB tool functions ────────────────────────────────────────────────────

def get_latest_knowledge(
    limit: Annotated[int, "Number of items to return (1-20)"] = 8,
    tags: Annotated[Optional[str], "Comma-separated tags, e.g. 'ai,markets'"] = None,
) -> str:
    """
    Fetch the latest knowledge items from AgentDB — a curated real-time
    knowledge base updated Mon/Wed/Fri covering markets, technology, science,
    philosophy, and current events.
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


def search_knowledge(
    query: Annotated[str, "Natural language search query"],
    limit: Annotated[int, "Number of results (1-10)"] = 5,
) -> str:
    """
    Semantic search across AgentDB. Use when you need specific information
    on a topic. Requires a Pro API key.
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{AGENTDB_URL}/v1/knowledge/search",
            headers={"X-API-Key": AGENTDB_KEY},
            params={"q": query, "limit": limit},
        )
        if resp.status_code == 403:
            return "Semantic search requires Pro. Using latest — upgrade at https://agentdb.dev/pricing"
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
        if item.get("summary"):
            lines.append(item["summary"])
        kp = body.get("key_points", [])
        if kp:
            for k in kp[:3]:
                lines.append(f"  • {k}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


# ── AutoGen agents ────────────────────────────────────────────────────────────

def build_agents():
    llm_config = get_llm_config()

    assistant = autogen.AssistantAgent(
        name="ResearchAssistant",
        system_message=(
            "You are a research assistant with access to AgentDB, a curated "
            "real-time knowledge base updated Mon/Wed/Fri. Always check AgentDB "
            "before answering questions about current events, markets, technology, "
            "or science. Cite your sources. When you have a complete answer, "
            "end your response with TERMINATE."
        ),
        llm_config=llm_config,
    )

    user_proxy = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
        code_execution_config=False,
    )

    # Register tools on both agents
    autogen.register_function(
        get_latest_knowledge,
        caller=assistant,
        executor=user_proxy,
        name="get_latest_knowledge",
        description="Fetch latest knowledge items from AgentDB",
    )

    autogen.register_function(
        search_knowledge,
        caller=assistant,
        executor=user_proxy,
        name="search_knowledge",
        description="Semantic search across AgentDB",
    )

    return assistant, user_proxy


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not AGENTDB_KEY:
        print("Set AGENTDB_API_KEY. Get a free key:")
        print("  curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \\")
        print("       -H 'Content-Type: application/json' -d '{}'")
        sys.exit(1)

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Question: ").strip()
    print(f"\nQuestion: {question}\n{'─' * 60}\n")

    assistant, user_proxy = build_agents()
    user_proxy.initiate_chat(assistant, message=question)


if __name__ == "__main__":
    main()
