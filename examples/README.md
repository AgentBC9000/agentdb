# AgentDB — Example Agents

Three working agents you can copy-paste and run in under 5 minutes.

Get a free API key first:
```bash
curl -s -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \
  -H "Content-Type: application/json" -d '{}' | python3 -m json.tool
```

---

## 01 — Daily Briefing

**`01_daily_briefing.py`** — No LLM needed. Fetches today's knowledge items and prints a formatted briefing.

```bash
pip install httpx
AGENTDB_API_KEY=adb_xxx python 01_daily_briefing.py
AGENTDB_API_KEY=adb_xxx python 01_daily_briefing.py --tags ai,markets
AGENTDB_API_KEY=adb_xxx python 01_daily_briefing.py --type video --limit 5
```

---

## 02 — Local LLM RAG (Ollama)

**`02_local_llm_rag.py`** — Gives your local Ollama model access to current events. Works with any OpenAI-compatible server (LM Studio, llama.cpp).

```bash
pip install httpx
ollama pull llama3.2

AGENTDB_API_KEY=adb_xxx python 02_local_llm_rag.py "What's happening in AI this week?"
AGENTDB_API_KEY=adb_xxx python 02_local_llm_rag.py "Summarise today's market news"

# Custom model/endpoint:
AGENTDB_API_KEY=adb_xxx OLLAMA_MODEL=mistral OLLAMA_URL=http://localhost:11434 \
    python 02_local_llm_rag.py "What are researchers saying about quantum computing?"
```

---

## 03 — Claude Research Agent (tool use)

**`03_claude_research_agent.py`** — Claude autonomously decides when to call AgentDB, fetches the right context, and returns a grounded answer.

```bash
pip install anthropic httpx

ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx \
    python 03_claude_research_agent.py "What's the latest in AI safety research?"

echo "Summarise today's market news" | \
    ANTHROPIC_API_KEY=sk-ant-xxx AGENTDB_API_KEY=adb_xxx python 03_claude_research_agent.py
```

---

## MCP server (Claude Code / Claude Desktop)

For the cleanest integration, use the MCP server — AgentDB tools appear natively inside Claude's tool use without any code:

```json
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
```

See the [main README](../README.md) for full setup instructions.

---

## What AgentDB provides

Updated **Mon / Wed / Fri at 07:00 UTC** from 14 curated sources:

- Bloomberg, CNBC, Reuters, Prof G Markets, Rebel Capitalist
- Lex Fridman, Y Combinator
- Closer To Truth, Bernardo Kastrup
- Hacker News, Ars Technica, Quanta Magazine, Marginal Revolution, Zero Hedge

Full source list: `GET https://agentdb-production-9ba0.up.railway.app/v1/knowledge/sources`
