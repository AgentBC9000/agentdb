#!/usr/bin/env python3
"""
AgentDB + LangGraph — Research Agent
=====================================
A LangGraph agent that uses AgentDB as a tool to answer questions
with current, real-world context.

Usage:
    pip install langgraph langchain-anthropic httpx

    ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx \\
        python 04_langgraph_agent.py "What's happening in AI this week?"

Get an AgentDB key (free):
    curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \\
         -H "Content-Type: application/json" -d '{}'

MCP alternative — skip all this code with 4 lines in ~/.claude.json:
    {
      "mcpServers": {
        "agentdb": {
          "type": "stdio",
          "command": "uv",
          "args": ["run", "/path/to/agentdb/mcp/server.py"],
          "env": { "AGENTDB_API_KEY": "adb_xxx" }
        }
      }
    }
"""

import os
import sys
import json
from typing import Annotated, Optional

try:
    import httpx
    from langchain_anthropic import ChatAnthropic
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode, tools_condition
    from typing_extensions import TypedDict
except ImportError:
    print("Install dependencies:  pip install langgraph langchain-anthropic httpx")
    sys.exit(1)

AGENTDB_URL = "https://agentdb-production-9ba0.up.railway.app"
AGENTDB_KEY = os.environ.get("AGENTDB_API_KEY", "")


# ── AgentDB tools ─────────────────────────────────────────────────────────────

@tool
def get_latest_knowledge(limit: int = 8, tags: Optional[str] = None) -> str:
    """
    Fetch the latest knowledge items from AgentDB — a curated real-time
    knowledge base updated Mon/Wed/Fri covering markets, technology, science,
    philosophy, and current events.

    Args:
        limit: Number of items to return (1-20)
        tags: Comma-separated tags to filter by, e.g. 'ai,markets'
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


@tool
def search_knowledge(query: str, limit: int = 5) -> str:
    """
    Semantic search across AgentDB. Use this when you need information
    on a specific topic. Returns the most relevant results.
    Requires a Pro API key — falls back to latest items on trial.

    Args:
        query: Natural language search query
        limit: Number of results (1-10)
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{AGENTDB_URL}/v1/knowledge/search",
            headers={"X-API-Key": AGENTDB_KEY},
            params={"q": query, "limit": limit},
        )
        if resp.status_code == 403:
            return "Semantic search requires Pro. Using latest items instead — upgrade at https://agentdb.dev/pricing"
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
            lines.append("Key points: " + " | ".join(kp[:3]))
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


# ── LangGraph setup ───────────────────────────────────────────────────────────

class State(TypedDict):
    messages: Annotated[list, add_messages]


tools = [get_latest_knowledge, search_knowledge]
llm = ChatAnthropic(model="claude-opus-4-5").bind_tools(tools)


def agent_node(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")
app = graph.compile()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not AGENTDB_KEY:
        print("Set AGENTDB_API_KEY. Get a free key:")
        print("  curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \\")
        print("       -H 'Content-Type: application/json' -d '{}'")
        sys.exit(1)

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Question: ").strip()
    print(f"\nQuestion: {question}\n{'─' * 60}")

    for event in app.stream({"messages": [HumanMessage(content=question)]}):
        for value in event.values():
            msg = value["messages"][-1]
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
                print(msg.content)

    print("─" * 60)


if __name__ == "__main__":
    main()
