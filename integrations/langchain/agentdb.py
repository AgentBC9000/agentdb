"""AgentDB retriever — real-time curated knowledge for AI agents.

This module provides a LangChain retriever that fetches up-to-date, pre-summarised
knowledge from the AgentDB API (https://agentdb.dev).

AgentDB ingests YouTube channels, podcasts, and blogs on a Monday/Wednesday/Friday
schedule, summarises each item with Claude, and exposes the results via a structured
REST API with optional semantic vector search.

Quickstart::

    from langchain_community.retrievers import AgentDBRetriever

    retriever = AgentDBRetriever(api_key="agentdb-...")
    docs = retriever.invoke("what happened with AI regulation this week")

Sign up for a free API key at https://agentdb.dev
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

import httpx
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

_BASE_URL = "https://agentdb-production-9ba0.up.railway.app"
_LATEST_PATH = "/v1/knowledge/latest"
_SEARCH_PATH = "/v1/knowledge/search"

ContentType = Literal["article", "video", "podcast", "data", "research"]
Topic = Literal[
    "ai_safety",
    "markets",
    "startups",
    "technology",
    "science",
    "philosophy",
    "economics",
]


class AgentDBRetriever(BaseRetriever):
    """Retriever that fetches real-time, pre-summarised knowledge from AgentDB.

    AgentDB is a curated knowledge API for AI agents. It continuously ingests
    YouTube channels, podcasts, and blog feeds, summarises each item with Claude,
    and makes the results available via a structured REST API with optional
    semantic vector search.

    **Setup:**

    Sign up for a free API key at https://agentdb.dev, then set the
    ``AGENTDB_API_KEY`` environment variable or pass ``api_key`` directly::

        export AGENTDB_API_KEY="agentdb-..."

    **Instantiate:**

    .. code-block:: python

        from langchain_community.retrievers import AgentDBRetriever

        # Semantic search (Pro tier) — returns most relevant items for a query
        retriever = AgentDBRetriever(api_key="agentdb-...", mode="search")

        # Latest items — returns newest entries, optionally filtered
        retriever = AgentDBRetriever(
            api_key="agentdb-...",
            mode="latest",
            k=10,
            content_type="podcast",
            tags="ai,machine-learning",
        )

    **Invoke:**

    .. code-block:: python

        # For mode="search", the query string drives semantic similarity
        docs = retriever.invoke("AI regulation news this week")

        # For mode="latest", the query string is ignored — use filters instead
        docs = retriever.invoke("")

    Each returned ``Document`` has:

    - ``page_content``: 2-3 paragraph summary of the item
    - ``metadata``: title, content_type, tags, confidence, published_at, source_url,
      key_points (list), id

    **Use in a chain:**

    .. code-block:: python

        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnablePassthrough
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini")
        retriever = AgentDBRetriever(api_key="agentdb-...")

        prompt = ChatPromptTemplate.from_template(
            "Answer based on this recent knowledge:\\n\\n{context}\\n\\nQuestion: {question}"
        )

        chain = (
            {"context": retriever | _format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
        )

        answer = chain.invoke("What are the latest AI safety developments?")
    """

    api_key: Optional[str] = None
    """AgentDB API key. Falls back to AGENTDB_API_KEY env var."""

    mode: Literal["search", "latest"] = "search"
    """
    Retrieval mode.

    - ``"search"``: semantic vector search — uses the query to find the most
      relevant items across the knowledge base. Requires Pro tier.
    - ``"latest"``: returns the newest items, optionally filtered by
      content_type or tags. Query string is ignored.
    """

    k: int = 10
    """Maximum number of documents to return (1-50 for search, 1-100 for latest)."""

    content_type: Optional[ContentType] = None
    """Filter by content type: ``"article"``, ``"video"``, ``"podcast"``,
    ``"data"``, or ``"research"``. Only applied in ``mode="latest"``."""

    tags: Optional[str] = None
    """Comma-separated tag filter, e.g. ``"ai,machine-learning"``.
    Uses PostgreSQL array overlap — any matching tag is included.
    Only applied in ``mode="latest"``."""

    min_confidence: Optional[float] = None
    """Minimum confidence score (0.0–1.0). Items below this threshold are
    excluded from results. Confidence is assigned by Claude during ingestion."""

    base_url: str = _BASE_URL
    """AgentDB API base URL. Override for self-hosted deployments."""

    timeout: float = 10.0
    """HTTP request timeout in seconds."""

    # ── internal helpers ────────────────────────────────────────────────────

    def _resolved_api_key(self) -> str:
        key = self.api_key or os.environ.get("AGENTDB_API_KEY", "")
        if not key:
            raise ValueError(
                "No AgentDB API key found. Pass api_key= or set the "
                "AGENTDB_API_KEY environment variable. "
                "Get a free key at https://agentdb.dev"
            )
        return key

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._resolved_api_key()}",
            "Accept": "application/json",
        }

    def _build_latest_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": min(self.k, 100), "page": 1}
        if self.content_type:
            params["content_type"] = self.content_type
        if self.tags:
            params["tags"] = self.tags
        return params

    def _build_search_params(self, query: str) -> Dict[str, Any]:
        return {"q": query, "limit": min(self.k, 50)}

    def _items_to_documents(self, items: List[Dict[str, Any]]) -> List[Document]:
        docs = []
        for item in items:
            # Build rich page_content from summary + key_points
            body = item.get("body") or {}
            key_points: List[str] = body.get("key_points", [])

            content_parts = [item.get("summary", "").strip()]
            if key_points:
                content_parts.append(
                    "Key points:\n"
                    + "\n".join(f"• {p}" for p in key_points)
                )
            page_content = "\n\n".join(p for p in content_parts if p)

            # Apply client-side confidence filter if set
            confidence = item.get("confidence") or 0.0
            if self.min_confidence is not None and confidence < self.min_confidence:
                continue

            metadata: Dict[str, Any] = {
                "id": item.get("id"),
                "title": item.get("title"),
                "content_type": item.get("content_type"),
                "tags": item.get("tags") or [],
                "confidence": confidence,
                "published_at": item.get("published_at"),
                "source_url": body.get("source_url") or item.get("source_url"),
                "key_points": key_points,
            }
            # Include similarity score when present (search mode)
            if "similarity" in item:
                metadata["similarity"] = item["similarity"]

            docs.append(Document(page_content=page_content, metadata=metadata))

        return docs

    # ── sync ────────────────────────────────────────────────────────────────

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Fetch documents from AgentDB synchronously.

        Args:
            query: Natural language query (used in ``mode="search"``; ignored
                   in ``mode="latest"``).
            run_manager: LangChain callback handler.

        Returns:
            List of :class:`~langchain_core.documents.Document` objects.
        """
        if self.mode == "search":
            if not query.strip():
                raise ValueError(
                    "A non-empty query string is required for mode='search'. "
                    "Use mode='latest' to fetch recent items without a query."
                )
            url = f"{self.base_url}{_SEARCH_PATH}"
            params = self._build_search_params(query)
        else:
            url = f"{self.base_url}{_LATEST_PATH}"
            params = self._build_latest_params()

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self._build_headers(), params=params)

        response.raise_for_status()
        data = response.json()
        return self._items_to_documents(data.get("items", []))

    # ── async ───────────────────────────────────────────────────────────────

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Fetch documents from AgentDB asynchronously.

        Args:
            query: Natural language query (used in ``mode="search"``; ignored
                   in ``mode="latest"``).
            run_manager: LangChain callback handler.

        Returns:
            List of :class:`~langchain_core.documents.Document` objects.
        """
        if self.mode == "search":
            if not query.strip():
                raise ValueError(
                    "A non-empty query string is required for mode='search'. "
                    "Use mode='latest' to fetch recent items without a query."
                )
            url = f"{self.base_url}{_SEARCH_PATH}"
            params = self._build_search_params(query)
        else:
            url = f"{self.base_url}{_LATEST_PATH}"
            params = self._build_latest_params()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url, headers=self._build_headers(), params=params
            )

        response.raise_for_status()
        data = response.json()
        return self._items_to_documents(data.get("items", []))
