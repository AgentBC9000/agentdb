# AgentDB

**Fresh RAG context for AI agents — updated Mon/Wed/Fri.**

AgentDB is a curated knowledge base your agent queries at inference time. 40 sources — AI/tech, startups, alternative markets, and emerging economies — scraped, AI-summarised, and structured into agent-ready JSON.

Connect it to Claude Desktop, Cursor, or any MCP-compatible agent in under 2 minutes.

→ **[Request access](mailto:agentbc9000@gmail.com?subject=AgentDB%20Access%20Request)**

---

## MCP server (Claude Desktop / Cursor / Claude Code)

The AgentDB MCP server gives your agent two tools: `get_latest_knowledge` and `search_knowledge`.

### Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) — it handles Python automatically:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentdb": {
      "command": "uv",
      "args": ["run", "/absolute/path/to/agentdb/mcp/server.py"],
      "env": {
        "AGENTDB_SUPABASE_URL": "your-supabase-url",
        "AGENTDB_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Claude Code (global — all sessions)

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "agentdb": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "/absolute/path/to/agentdb/mcp/server.py"],
      "env": {
        "AGENTDB_SUPABASE_URL": "your-supabase-url",
        "AGENTDB_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Claude Code (project-level)

Add `.mcp.json` to your project root:

```json
{
  "mcpServers": {
    "agentdb": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "/absolute/path/to/agentdb/mcp/server.py"],
      "env": {
        "AGENTDB_SUPABASE_URL": "your-supabase-url",
        "AGENTDB_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Test it manually

```bash
AGENTDB_SUPABASE_URL=https://xxxx.supabase.co \
AGENTDB_API_KEY=your-key \
uv run mcp/server.py
```

---

## Available tools

### `get_latest_knowledge`

Fetch the most recent items, optionally filtered by tag or content type.

```
Parameters:
  limit         int     Items to return (1–50, default 10)
  tags          string  Comma-separated tag filter, e.g. "ai,startups"
  content_type  string  article | video | research | data
```

Example response item:

```json
{
  "title": "DeepSeek v4 and the limits of scaling",
  "content_type": "article",
  "summary": "DeepSeek's mixture-of-experts approach cuts inference cost...",
  "body": {
    "source_name": "Ars Technica",
    "key_points": [
      "MoE reduces active parameters by 4× at inference",
      "Outperforms GPT-4o on coding benchmarks",
      "Open weights released under MIT licence"
    ]
  },
  "tags": ["ai", "llm", "open-source"],
  "confidence": 0.93,
  "published_at": "2026-05-26T07:00:00Z"
}
```

### `search_knowledge`

Search titles and summaries by keyword.

```
Parameters:
  query   string  Keyword or phrase (required)
  limit   int     Results to return (1–20, default 5)
```

---

## Sources

40 sources · updated Mon/Wed/Fri at 07:00 UTC · no paywalls, no wire services.

| Category | Sources |
|---|---|
| **Technology / AI** | Lex Fridman Podcast, Dwarkesh Podcast, Hard Fork, This Week in Tech, ChinaTalk, Ars Technica, Import AI, TLDR Tech, 404 Media, Wired, arXiv AI |
| **Startups / VC** | Acquired, How I Built This, Y Combinator Blog, Y Combinator (YouTube), TechCrunch, The Verge, Entrepreneur, The Generalist, Parsers VC |
| **Markets / Macro** | All-In Podcast, Prof G Markets, Zero Hedge, Calculated Risk, Econbrowser, A Wealth of Common Sense, The Big Picture, The Daily Upside, Asymco, Noahpinion |
| **Emerging Markets** | Rest of World, TechCabal, Techpoint Africa, Disrupt Africa, Mint (India), Asia Times, The Hindu Business Line |
| **Policy / Regulation** | Politico Europe, arXiv Policy |

---

## Pricing

| Plan | Price | Requests |
|---|---|---|
| Trial | Free — 14 days | 100 / day |
| Basic | £29 / month | 1,000 / day |
| Pro | £79 / month | Unlimited + custom sources |

[Request access →](mailto:agentbc9000@gmail.com?subject=AgentDB%20Access%20Request)

---

## How it works

```
GitHub Actions (Mon/Wed/Fri 07:00 UTC)
    ↓
scraper/run.py — fetches RSS/HTML from 40 sources
    ↓
scraper/summariser.py — DeepSeek Flash → structured JSON
    ↓
scraper/ingest.py — writes to Supabase via PostgREST
    ↓
mcp/server.py — exposes knowledge as MCP tools
```

**Stack:** Python · GitHub Actions · DeepSeek Flash · Supabase (pgvector) · Cloudflare Pages

**Cost to run:** ~£2–3/month (DeepSeek API calls only — everything else is free tier).

---

## Repo structure

```
mcp/
  server.py           # MCP server — connect to Claude Desktop / Cursor
scraper/
  run.py              # Orchestrator — called by GitHub Actions
  sources.py          # 40 source definitions (RSS URLs, categories)
  scraper.py          # HTTP fetch + HTML parsing
  summariser.py       # DeepSeek Flash summarisation
  ingest.py           # Supabase PostgREST write
  keepalive.py        # Keeps Supabase free tier active
db/
  migrations/
    001_create_knowledge_table.sql
    002_read_policy.sql
.github/
  workflows/
    scraper.yml       # Mon/Wed/Fri scrape cron
    keepalive.yml     # Every 6h Supabase ping
index.html            # Website (agentdb.pages.dev)
```

---

## Self-hosting

Clone the repo and set up GitHub Actions secrets:

```
DEEPSEEK_API_KEY       — DeepSeek API key (api.deepseek.com)
SUPABASE_URL           — Supabase project URL
SUPABASE_SERVICE_KEY   — Supabase service role key (for writes)
AGENTDB_DATABASE_URL   — Supabase direct DB URL (for keepalive)
RESEND_API_KEY         — Resend API key (for run reports)
REPORT_EMAIL           — Email to send scraper reports to
```

Run the SQL migrations in Supabase → SQL Editor:
- `db/migrations/001_create_knowledge_table.sql`
- `db/migrations/002_read_policy.sql`

Enable Row Level Security on the `knowledge` table, then trigger a manual run from GitHub Actions → AgentDB Scraper → Run workflow.

---

## Contact

[agentbc9000@gmail.com](mailto:agentbc9000@gmail.com) · [agentdb.pages.dev](https://agentdb.pages.dev)
