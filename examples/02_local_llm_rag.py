#!/usr/bin/env python3
"""
AgentDB + Local LLM — Real-time RAG Agent
==========================================
Gives your local LLM (Ollama / LM Studio / any OpenAI-compatible server)
access to current events and fresh knowledge without training cutoff limits.

How it works:
  1. Takes your question as input
  2. Searches AgentDB for relevant knowledge (semantic search, Pro) or
     fetches latest items (trial) as context
  3. Sends context + question to your local LLM
  4. Returns a grounded, up-to-date answer

Usage:
    pip install httpx
    ollama pull llama3.2   # or any model

    # With AgentDB Pro key (semantic search):
    AGENTDB_API_KEY=adb_xxx python 02_local_llm_rag.py "What's happening in AI this week?"

    # With trial key (latest items as context):
    AGENTDB_API_KEY=adb_xxx python 02_local_llm_rag.py "Summarise today's market news"

    # Custom local LLM endpoint / model:
    AGENTDB_API_KEY=adb_xxx OLLAMA_MODEL=mistral OLLAMA_URL=http://localhost:11434 \\
        python 02_local_llm_rag.py "What are researchers saying about quantum computing?"

Get a free API key: https://agentdb-production-9ba0.up.railway.app/v1/auth/register
"""

import os
import sys
import json

try:
    import httpx
except ImportError:
    print("Install httpx first:  pip install httpx")
    sys.exit(1)

AGENTDB_URL  = "https://agentdb-production-9ba0.up.railway.app"
AGENTDB_KEY  = os.environ.get("AGENTDB_API_KEY", "")

OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


# ── AgentDB helpers ───────────────────────────────────────────────────────────

def search_knowledge(query: str, limit: int = 5) -> list:
    """Semantic search — Pro tier. Falls back to latest on 403."""
    resp = httpx.get(
        f"{AGENTDB_URL}/v1/knowledge/search",
        headers={"X-API-Key": AGENTDB_KEY},
        params={"q": query, "limit": limit},
        timeout=15,
    )
    if resp.status_code == 403:
        # Trial key — fall back to latest items
        print("  (Semantic search requires Pro — using latest items instead)")
        return get_latest(limit=limit * 2)
    resp.raise_for_status()
    return resp.json()["items"]


def get_latest(limit: int = 10) -> list:
    resp = httpx.get(
        f"{AGENTDB_URL}/v1/knowledge/latest",
        headers={"X-API-Key": AGENTDB_KEY},
        params={"limit": limit},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["items"]


def format_context(items: list) -> str:
    """Format knowledge items into a context block for the LLM prompt."""
    parts = []
    for item in items:
        body       = item.get("body") or {}
        key_points = body.get("key_points", [])
        source     = body.get("source_name", "")
        pub        = str(item.get("published_at", ""))[:10]

        block = [f"TITLE: {item['title']}"]
        if source:
            block.append(f"SOURCE: {source}  DATE: {pub}")
        if item.get("summary"):
            block.append(f"SUMMARY: {item['summary']}")
        if key_points:
            block.append("KEY POINTS:")
            for kp in key_points[:4]:
                block.append(f"  - {kp}")
        parts.append("\n".join(block))

    return "\n\n---\n\n".join(parts)


# ── Ollama / OpenAI-compatible LLM ───────────────────────────────────────────

def ask_local_llm(context: str, question: str) -> str:
    """Send context + question to local LLM via Ollama's OpenAI-compatible API."""
    system_prompt = (
        "You are a helpful assistant with access to a curated real-time knowledge base. "
        "Answer the user's question using ONLY the provided context. "
        "If the context doesn't contain enough information, say so honestly. "
        "Cite sources when possible. Be concise and factual."
    )

    user_message = f"""Here is the latest knowledge from AgentDB:

{context}

---

Question: {question}"""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "stream": False,
    }

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except httpx.ConnectError:
        return (
            f"Could not connect to Ollama at {OLLAMA_URL}.\n"
            "Make sure Ollama is running: https://ollama.com/download\n"
            f"Then pull a model:  ollama pull {OLLAMA_MODEL}"
        )
    except Exception as exc:
        return f"LLM error: {exc}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print("Usage: python 02_local_llm_rag.py \"your question here\"")
        sys.exit(1)

    if not AGENTDB_KEY:
        print("Set AGENTDB_API_KEY environment variable.")
        print("Get a free key: curl -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register -H 'Content-Type: application/json' -d '{}'")
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    print(f"\nQuestion: {question}")
    print(f"Model:    {OLLAMA_MODEL} @ {OLLAMA_URL}")
    print()

    print("Fetching context from AgentDB...", end="", flush=True)
    items = search_knowledge(question, limit=5)
    print(f" {len(items)} items")

    context = format_context(items)

    print(f"Asking {OLLAMA_MODEL}...\n")
    print("─" * 60)
    answer = ask_local_llm(context, question)
    print(answer)
    print("─" * 60)
    print()
    print(f"Context from {len(items)} AgentDB items  |  agentdb.dev")
    print()


if __name__ == "__main__":
    main()
