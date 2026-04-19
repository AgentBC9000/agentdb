#!/usr/bin/env python3
"""
AgentDB + CrewAI — Research Crew
==================================
A two-agent CrewAI crew: a Researcher fetches context from AgentDB,
an Analyst synthesises it into a clear briefing.

Usage:
    pip install crewai httpx

    ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx \\
        python 05_crewai_agent.py "What's the latest in quantum computing?"

Get an AgentDB key (free):
    curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \\
         -H "Content-Type: application/json" -d '{}'
"""

import os
import sys
from typing import Optional, Type

try:
    import httpx
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field
except ImportError:
    print("Install dependencies:  pip install crewai httpx")
    sys.exit(1)

AGENTDB_URL = "https://agentdb-production-9ba0.up.railway.app"
AGENTDB_KEY = os.environ.get("AGENTDB_API_KEY", "")


# ── AgentDB tools ─────────────────────────────────────────────────────────────

class LatestKnowledgeInput(BaseModel):
    limit: int = Field(default=8, description="Number of items to return (1-20)")
    tags: Optional[str] = Field(default=None, description="Comma-separated tags, e.g. 'ai,markets'")


class GetLatestKnowledgeTool(BaseTool):
    name: str = "get_latest_knowledge"
    description: str = (
        "Fetch the latest knowledge items from AgentDB — a curated real-time "
        "knowledge base updated Mon/Wed/Fri covering markets, technology, science, "
        "philosophy, and current events. Use this to get fresh context."
    )
    args_schema: Type[BaseModel] = LatestKnowledgeInput

    def _run(self, limit: int = 8, tags: Optional[str] = None) -> str:
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


class SearchKnowledgeInput(BaseModel):
    query: str = Field(description="Natural language search query")
    limit: int = Field(default=5, description="Number of results (1-10)")


class SearchKnowledgeTool(BaseTool):
    name: str = "search_knowledge"
    description: str = (
        "Semantic search across AgentDB. Use this when you need information "
        "on a specific topic rather than just the latest items."
    )
    args_schema: Type[BaseModel] = SearchKnowledgeInput

    def _run(self, query: str, limit: int = 5) -> str:
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
        if item.get("summary"):
            lines.append(item["summary"])
        kp = body.get("key_points", [])
        if kp:
            lines.append("Key points:")
            for k in kp[:3]:
                lines.append(f"  • {k}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


# ── Crew setup ────────────────────────────────────────────────────────────────

agentdb_tools = [GetLatestKnowledgeTool(), SearchKnowledgeTool()]

researcher = Agent(
    role="Knowledge Researcher",
    goal="Find the most relevant and recent information on the given topic using AgentDB",
    backstory=(
        "You are an expert researcher with access to AgentDB, a curated real-time "
        "knowledge base updated Mon/Wed/Fri. You know how to search for exactly the "
        "right context and surface the most relevant recent developments."
    ),
    tools=agentdb_tools,
    verbose=True,
)

analyst = Agent(
    role="Research Analyst",
    goal="Synthesise research findings into a clear, concise briefing",
    backstory=(
        "You are a sharp analyst who takes raw research and turns it into clear, "
        "actionable insights. You always cite your sources and highlight the most "
        "important developments."
    ),
    verbose=True,
)


def build_crew(question: str) -> Crew:
    research_task = Task(
        description=f"Research the following topic using AgentDB: {question}\n"
                    "Fetch relevant knowledge items and compile the key findings.",
        expected_output="A comprehensive set of relevant knowledge items with summaries and key points.",
        agent=researcher,
    )

    analysis_task = Task(
        description="Synthesise the research findings into a clear briefing that directly answers: "
                    f"{question}\nCite sources and highlight the most important developments.",
        expected_output="A concise, well-structured briefing with source citations.",
        agent=analyst,
        context=[research_task],
    )

    return Crew(
        agents=[researcher, analyst],
        tasks=[research_task, analysis_task],
        process=Process.sequential,
        verbose=True,
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

    crew = build_crew(question)
    result = crew.kickoff()

    print(f"\n{'─' * 60}")
    print("FINAL BRIEFING")
    print("─" * 60)
    print(result)
    print("─" * 60)
    print("Powered by AgentDB — agentdb.dev")


if __name__ == "__main__":
    main()
