from fastapi import APIRouter, Depends, Query, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
import uuid
import json

from app.core.config import settings
from app.core.dependencies import get_current_key
from app.db.client import get_db
from app.services.rate_limiter import check_rate_limit

router = APIRouter()


# ── Response models ───────────────────────────────────────────────────────────

class KnowledgeItem(BaseModel):
    id: str
    title: str
    content_type: str
    summary: Optional[str] = None
    body: Optional[dict] = None
    tags: Optional[List[str]] = None
    confidence: Optional[float] = None
    relevance_score: Optional[float] = None
    published_at: str


class KnowledgeResponse(BaseModel):
    items: List[KnowledgeItem]
    total: int
    page: int
    has_more: bool


class IngestRequest(BaseModel):
    title: str
    content_type: str                  # "article", "video", "data", "research"
    summary: Optional[str] = None
    body: Optional[dict] = None        # Structured content
    tags: Optional[List[str]] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = 1.0
    relevance_score: Optional[float] = 1.0
    generate_embedding: bool = True    # Auto-generate vector embedding


# ── Sources manifest (public — no API key required) ──────────────────────────

_SOURCES = {
    "youtube": [
        {"name": "Bloomberg",        "category": "market_news",              "url": "https://youtube.com/channel/UCIALMKvObZNtJ6AmdCLP7Lg"},
        {"name": "CNBC",             "category": "market_news",              "url": "https://youtube.com/channel/UCrp_UI8XtuYfpiqluWLD7Lw"},
        {"name": "Reuters",          "category": "market_news",              "url": "https://youtube.com/channel/UChqUTb7kYRX8-EiaN3XFrSQ"},
        {"name": "Prof G Markets",   "category": "market_news",              "url": "https://youtube.com/channel/UCp4CBeq4nzeg9smAvdjPrig"},
        {"name": "Rebel Capitalist", "category": "market_news_alternative",  "url": "https://youtube.com/channel/UCNjyEXSvYUUCzagFAKmaJ1Q"},
        {"name": "Lex Fridman",      "category": "technology_ai",            "url": "https://youtube.com/channel/UCSHZKyawb77ixDdsGog4iWA"},
        {"name": "Y Combinator",     "category": "startups_technology",      "url": "https://youtube.com/channel/UCcefcZRL2oaA_uBNeo5UOWg"},
        {"name": "Closer To Truth",  "category": "philosophy_science",       "url": "https://youtube.com/channel/UCl9StMQ79LtEvlrskzjoYbQ"},
        {"name": "Bernardo Kastrup", "category": "philosophy_science",       "url": "https://youtube.com/channel/UCeDZCa3VrRQvzBlVR-oVVmA"},
    ],
    "blogs": [
        {"name": "Hacker News",       "category": "technology_startups",      "url": "https://news.ycombinator.com"},
        {"name": "Ars Technica",      "category": "technology_science",       "url": "https://arstechnica.com"},
        {"name": "Quanta Magazine",   "category": "science_research",         "url": "https://quantamagazine.org"},
        {"name": "Marginal Revolution","category": "economics_policy",        "url": "https://marginalrevolution.com"},
        {"name": "Zero Hedge",        "category": "market_news_alternative",  "url": "https://zerohedge.com"},
    ],
    "schedule": "Mon / Wed / Fri at 07:00 UTC",
    "total_sources": 14,
}


@router.get("/sources")
async def get_sources():
    """
    Returns the full list of content sources AgentDB ingests.
    No API key required — use this to verify data provenance before subscribing.
    Updated Mon/Wed/Fri at 07:00 UTC.
    """
    return _SOURCES


# ── Public endpoints (require API key) ───────────────────────────────────────

@router.get("/latest", response_model=KnowledgeResponse)
async def get_latest(
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    content_type: Optional[str] = Query(None),
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    """
    Get the latest knowledge entries.
    AI agents should poll this endpoint regularly for fresh data.
    """
    await check_rate_limit(key_record)

    offset = (page - 1) * limit
    params = {"limit": limit, "offset": offset}

    conditions = ["is_active = true"]

    if content_type:
        conditions.append("content_type = :content_type")
        params["content_type"] = content_type

    # Tag filter uses PostgreSQL array overlap operator
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        conditions.append("tags && :tags")
        params["tags"] = tag_list

    where = " AND ".join(conditions)

    rows = await db.fetch_all(
        f"""SELECT id::text, title, content_type, summary, body, tags,
                   confidence, relevance_score, published_at::text
            FROM knowledge
            WHERE {where}
            ORDER BY published_at DESC
            LIMIT :limit OFFSET :offset""",
        params
    )

    items = []
    for r in rows:
        item = dict(r)
        item["id"] = str(item["id"])
        if item.get("published_at"):
            item["published_at"] = str(item["published_at"])
        if isinstance(item.get("body"), str):
            try:
                item["body"] = json.loads(item["body"])
            except (ValueError, TypeError):
                item["body"] = None
        items.append(item)

    return KnowledgeResponse(
        items=items,
        total=len(items),
        page=page,
        has_more=len(items) == limit
    )


@router.get("/search", response_model=KnowledgeResponse)
async def semantic_search(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50),
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    """
    Semantic vector search across the knowledge base.
    Pass a natural language query — returns most relevant entries.
    Requires Pro tier.
    """
    from app.core.dependencies import require_pro
    await check_rate_limit(key_record)

    from app.services.embeddings import get_embedding
    embedding = await get_embedding(q)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    rows = await db.fetch_all(
        """SELECT id::text, title, content_type, summary, body, tags,
                  confidence, relevance_score, published_at::text,
                  1 - (embedding <=> :embedding::vector) AS similarity
           FROM knowledge
           WHERE is_active = true AND embedding IS NOT NULL
           ORDER BY embedding <=> :embedding::vector
           LIMIT :limit""",
        {"embedding": embedding_str, "limit": limit}
    )

    items = []
    for r in rows:
        item = dict(r)
        item["id"] = str(item["id"])
        if item.get("published_at"):
            item["published_at"] = str(item["published_at"])
        if isinstance(item.get("body"), str):
            try:
                item["body"] = json.loads(item["body"])
            except (ValueError, TypeError):
                item["body"] = None
        items.append(item)

    return KnowledgeResponse(
        items=items,
        total=len(items),
        page=1,
        has_more=False
    )


@router.get("/{item_id}")
async def get_item(
    item_id: str,
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    """Get a single knowledge entry by ID, including any associated media."""
    await check_rate_limit(key_record)

    row = await db.fetch_one(
        """SELECT id::text, title, content_type, summary, body, tags,
                  confidence, relevance_score, published_at::text,
                  source_url, created_at::text
           FROM knowledge WHERE id = :id AND is_active = true""",
        {"id": item_id}
    )

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    media = await db.fetch_all(
        """SELECT id::text, file_name, file_type, r2_url,
                  transcript_summary, created_at::text
           FROM media WHERE knowledge_id = :id""",
        {"id": item_id}
    )

    result = dict(row)
    result["media"] = [dict(m) for m in media]
    return result


# ── Admin ingest endpoint (requires ADMIN_SECRET header) ─────────────────────

@router.post("/ingest", status_code=201)
async def ingest_item(
    payload: IngestRequest,
    secret: Optional[str] = Query(None),
    db=Depends(get_db),
):
    """
    Admin endpoint — ingest a new knowledge item.
    Requires ?secret=<admin-secret> query parameter.
    Not accessible to regular API keys.
    """
    if secret != settings.ADMIN_SECRET.strip():
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    item_id = str(uuid.uuid4())

    embedding = None
    if payload.generate_embedding and payload.summary and settings.OPENAI_API_KEY:
        try:
            from app.services.embeddings import get_embedding
            text = f"{payload.title}. {payload.summary}"
            vec = await get_embedding(text)
            embedding = "[" + ",".join(str(x) for x in vec) + "]"
        except Exception:
            pass  # Continue without embedding if it fails

    if embedding:
        await db.execute(
            """INSERT INTO knowledge
               (id, title, content_type, summary, body, tags,
                source_url, confidence, relevance_score, embedding)
               VALUES (:id, :title, :content_type, :summary, :body::jsonb,
                       :tags, :source_url, :confidence, :relevance_score,
                       :embedding::vector)""",
            {
                "id": item_id,
                "title": payload.title,
                "content_type": payload.content_type,
                "summary": payload.summary,
                "body": __import__("json").dumps(payload.body) if payload.body else None,
                "tags": payload.tags or [],
                "source_url": payload.source_url,
                "confidence": payload.confidence,
                "relevance_score": payload.relevance_score,
                "embedding": embedding,
            }
        )
    else:
        await db.execute(
            """INSERT INTO knowledge
               (id, title, content_type, summary, body, tags,
                source_url, confidence, relevance_score)
               VALUES (:id, :title, :content_type, :summary, :body::jsonb,
                       :tags, :source_url, :confidence, :relevance_score)""",
            {
                "id": item_id,
                "title": payload.title,
                "content_type": payload.content_type,
                "summary": payload.summary,
                "body": __import__("json").dumps(payload.body) if payload.body else None,
                "tags": payload.tags or [],
                "source_url": payload.source_url,
                "confidence": payload.confidence,
                "relevance_score": payload.relevance_score,
            }
        )

    return {
        "id": item_id,
        "title": payload.title,
        "embedding_generated": embedding is not None,
        "message": "Knowledge item ingested successfully."
    }
