# AgentDB

**Real-time curated knowledge API for AI agents.**

AgentDB is a knowledge base updated Mon/Wed/Fri with summaries from 14 sources spanning markets, technology, science, philosophy, and current events. Connect it to your AI agent so it always has fresh context — without you having to manage scraping, summarisation, or storage.

---

## Quick start

### 1. Get an API key

```bash
curl -s -X POST https://agentdb-production-9ba0.up.railway.app/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "name": "Your Agent"}'
```

Response:
```json
{
  "api_key": "adb_xxxxxxxxxxxxxxxxxxxx",
  "tier": "trial",
  "trial_expires_at": "2026-04-21T07:00:00",
  "message": "Welcome to AgentDB. Your 3-day trial has started."
}
```

Store your key — it's shown once.

### 2. Fetch the latest knowledge

```bash
curl https://agentdb-production-9ba0.up.railway.app/v1/knowledge/latest \
  -H "X-API-Key: adb_xxxxxxxxxxxxxxxxxxxx"
```

---

## MCP server (recommended for Claude)

The AgentDB MCP server exposes two tools directly inside Claude Code or Claude Desktop: `get_latest_knowledge` and `search_knowledge`.

### Install with uv (recommended)

[uv](https://docs.astral.sh/uv/) handles Python version management automatically — no need to install Python 3.10+ manually.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Claude Code — global config

Add to `~/.claude.json` (works in every Claude Code session):

```json
{
  "mcpServers": {
    "agentdb": {
      "type": "stdio",
      "command": "/path/to/uv",
      "args": ["run", "/path/to/agentdb/mcp/server.py"],
      "env": {
        "AGENTDB_API_KEY": "adb_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

Find your `uv` path with `which uv`. Find the server path with `realpath mcp/server.py` from this repo.

### Claude Code — project config

Add a `.mcp.json` to your project root:

```json
{
  "mcpServers": {
    "agentdb": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "/absolute/path/to/agentdb/mcp/server.py"],
      "env": {
        "AGENTDB_API_KEY": "adb_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
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
        "AGENTDB_API_KEY": "adb_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

### Run the MCP server manually (test it)

```bash
AGENTDB_API_KEY=adb_xxxxxxxxxxxxxxxxxxxx uv run mcp/server.py
```

### Available MCP tools

| Tool | Tier | Description |
|------|------|-------------|
| `get_latest_knowledge` | Trial + Pro | Fetch the N most recent items, optionally filtered by tags or content type |
| `search_knowledge` | Pro | Semantic vector search — find items most relevant to a natural language query |

---

## REST API reference

Base URL: `https://agentdb-production-9ba0.up.railway.app`

All endpoints (except `/health`, `/v1/auth/register`, and `/v1/knowledge/sources`) require:

```
X-API-Key: adb_xxxxxxxxxxxxxxxxxxxx
```

### Knowledge

| Method | Path | Tier | Description |
|--------|------|------|-------------|
| `GET` | `/v1/knowledge/latest` | Trial + Pro | Latest items; supports `limit`, `page`, `tags`, `content_type` |
| `GET` | `/v1/knowledge/search?q=...` | Pro | Semantic search |
| `GET` | `/v1/knowledge/{id}` | Trial + Pro | Single item by ID |
| `GET` | `/v1/knowledge/sources` | Public | List of all scraped sources |

#### Query parameters — `/latest`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Items per page (1–100) |
| `page` | int | 1 | Page number |
| `tags` | string | — | Comma-separated tag filter, e.g. `ai,markets` |
| `content_type` | string | — | `article`, `video`, `research`, or `data` |

#### Example response item

```json
{
  "id": "3e7c224c-...",
  "title": "Quantum Jamming and the Search for Principles Deeper Than Quantum Mechanics",
  "content_type": "article",
  "summary": "Researchers are exploring whether cryptographic protocols...",
  "body": {
    "category": "science_research",
    "key_points": ["...", "..."],
    "source_name": "Quanta Magazine"
  },
  "tags": ["quantum-mechanics", "cryptography", "causality"],
  "confidence": 0.92,
  "relevance_score": 0.92,
  "published_at": "2026-04-18T11:40:55+00:00"
}
```

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/auth/register` | Register and get a trial API key |
| `GET` | `/v1/auth/me` | Inspect your key (tier, usage, expiry) |

---

## Sources

AgentDB ingests from 14 sources, updated Mon/Wed/Fri at 07:00 UTC.

**YouTube channels** (video summaries)

| Source | Category |
|--------|----------|
| Bloomberg | market_news |
| CNBC | market_news |
| Reuters | market_news |
| Prof G Markets | market_news |
| Rebel Capitalist | market_news_alternative |
| Lex Fridman | technology_ai |
| Y Combinator | startups_technology |
| Closer To Truth | philosophy_science |
| Bernardo Kastrup | philosophy_science |

**Blogs / RSS** (article summaries)

| Source | Category |
|--------|----------|
| Hacker News | technology_startups |
| Ars Technica | technology_science |
| Quanta Magazine | science_research |
| Marginal Revolution | economics_policy |
| Zero Hedge | market_news_alternative |

Full machine-readable list: `GET /v1/knowledge/sources`

---

## Pricing

| Tier | Price | Rate limit | Features |
|------|-------|------------|----------|
| Trial | Free | 100 req/day | Latest items, 3 days |
| Pro | $20/month | 1,000 req/day | Latest + semantic search |
| Fleet | $99/month | 10,000 req/day | Everything, bulk access |

Upgrade via `/v1/payments/checkout` (Stripe or crypto).

---

## Self-hosting

```bash
git clone https://github.com/AgentBC9000/agentdb
cd agentdb
cp .env.example .env   # fill in ANTHROPIC_API_KEY, DATABASE_URL, ADMIN_SECRET
docker-compose up
```

The scraper runs independently — trigger it manually or set a cron:

```bash
cd scraper
ANTHROPIC_API_KEY=... AGENTDB_API_URL=... ADMIN_SECRET=... python run.py
```
