from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from pydantic import BaseModel

from app.core.dependencies import get_current_key
from app.db.client import get_db
from app.services.rate_limiter import check_rate_limit

router = APIRouter()


class KnowledgeItem(BaseModel):
    id: str
    title: str
    content_type: str
    summary: Optional[str]
    body: Optional[dict]
    tags: Optional[List[str]]
    confidence: Optional[float]
    relevance_score: Optional[float]
    published_at: str


class KnowledgeResponse(BaseModel):
    items: List[KnowledgeItem]
    total: int
    page: int
    has_more: bool


@router.get("/latest", response_model=KnowledgeResponse)
async def get_latest(
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    tags: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    await check_rate_limit(key_record)

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    offset = (page - 1) * limit

    query = """
        SELECT id, title, content_type, summary, body, tags,
               confidence, relevance_score, published_at
        FROM knowledge
        WHERE is_active = true
    """
    params = {}

    if tag_list:
        query += " AND tags && :tags"
        params["tags"] = tag_list

    if content_type:
        query += " AND content_type = :content_type"
        params["content_type"] = content_type

    query += " ORDER BY published_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    rows = await db.fetch_all(query, params)

    return KnowledgeResponse(
        items=[dict(r) for r in rows],
        total=len(rows),
        page=page,
        has_more=len(rows) == limit
    )


@router.get("/search")
async def semantic_search(
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    await check_rate_limit(key_record)

    from app.services.embeddings import get_embedding
    embedding = await get_embedding(q)

    rows = await db.fetch_all(
        """
        SELECT id, title, content_type, summary, body, tags,
               confidence, relevance_score, published_at
        FROM knowledge
        WHERE is_active = true
        ORDER BY embedding <=> :embedding
        LIMIT :limit
        """,
        {"embedding": str(embedding), "limit": limit}
    )

    return KnowledgeResponse(
        items=[dict(r) for r in rows],
        total=len(rows),
        page=1,
        has_more=False
    )


@router.get("/{item_id}")
async def get_item(
    item_id: str,
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    await check_rate_limit(key_record)

    row = await db.fetch_one(
        "SELECT * FROM knowledge WHERE id = :id AND is_active = true",
        {"id": item_id}
    )

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Item not found")

    media = await db.fetch_all(
        "SELECT * FROM media WHERE knowledge_id = :id",
        {"id": item_id}
    )

    result = dict(row)
    result["media"] = [dict(m) for m in media]
    return result
