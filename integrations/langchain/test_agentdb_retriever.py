"""Unit tests for AgentDBRetriever.

These tests use httpx's MockTransport to avoid live network calls.
Run with: pytest test_agentdb_retriever.py -v
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so the tests run without installing langchain-community
# ---------------------------------------------------------------------------

try:
    from langchain_community.retrievers.agentdb import AgentDBRetriever
except ImportError:
    import sys
    import types

    # Stub out langchain_core so the module can be imported standalone
    for mod in [
        "langchain_core",
        "langchain_core.callbacks",
        "langchain_core.documents",
        "langchain_core.retrievers",
    ]:
        if mod not in sys.modules:
            sys.modules[mod] = types.ModuleType(mod)

    import types as _types

    # Minimal BaseRetriever stub
    class _BaseRetriever:
        model_fields: Dict = {}

        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _Document:
        def __init__(self, page_content: str, metadata: Dict) -> None:
            self.page_content = page_content
            self.metadata = metadata

    sys.modules["langchain_core"].BaseRetriever = _BaseRetriever  # type: ignore
    sys.modules["langchain_core.retrievers"].BaseRetriever = _BaseRetriever  # type: ignore
    sys.modules["langchain_core.documents"].Document = _Document  # type: ignore
    sys.modules["langchain_core.callbacks"].CallbackManagerForRetrieverRun = object  # type: ignore
    sys.modules["langchain_core.callbacks"].AsyncCallbackManagerForRetrieverRun = object  # type: ignore

    # Now import from the local file
    import importlib.util, pathlib

    _spec = importlib.util.spec_from_file_location(
        "agentdb",
        pathlib.Path(__file__).parent / "agentdb.py",
    )
    _mod = importlib.util.module_from_spec(_spec)  # type: ignore
    _spec.loader.exec_module(_mod)  # type: ignore
    AgentDBRetriever = _mod.AgentDBRetriever  # type: ignore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ITEM: Dict[str, Any] = {
    "id": "abc-123",
    "title": "AI Safety Breakthrough at DeepMind",
    "content_type": "article",
    "summary": "DeepMind researchers published findings on scalable reward modelling.",
    "body": {
        "key_points": [
            "Reward models can be trained with 10x less data",
            "New evaluation benchmark released",
        ],
        "source_url": "https://deepmind.com/research/example",
    },
    "tags": ["ai-safety", "deepmind", "reinforcement-learning"],
    "confidence": 0.92,
    "relevance_score": 0.88,
    "published_at": "2026-04-18 07:00:00",
}

SAMPLE_RESPONSE: Dict[str, Any] = {
    "items": [SAMPLE_ITEM],
    "total": 1,
    "page": 1,
    "has_more": False,
}


def _make_transport(status: int = 200, body: Any = None) -> httpx.MockTransport:
    """Return an httpx mock transport that always returns the given status + JSON body."""
    payload = json.dumps(body or SAMPLE_RESPONSE).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=payload)

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


def test_requires_api_key_when_env_not_set() -> None:
    """ValueError raised when no key is available."""
    env_backup = os.environ.pop("AGENTDB_API_KEY", None)
    try:
        retriever = AgentDBRetriever()
        with pytest.raises(ValueError, match="No AgentDB API key"):
            retriever._resolved_api_key()
    finally:
        if env_backup is not None:
            os.environ["AGENTDB_API_KEY"] = env_backup


def test_resolves_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTDB_API_KEY", "agentdb-from-env")
    retriever = AgentDBRetriever()
    assert retriever._resolved_api_key() == "agentdb-from-env"


def test_resolves_api_key_from_param(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTDB_API_KEY", raising=False)
    retriever = AgentDBRetriever(api_key="agentdb-direct")
    assert retriever._resolved_api_key() == "agentdb-direct"


def test_default_mode_is_search() -> None:
    retriever = AgentDBRetriever(api_key="agentdb-test")
    assert retriever.mode == "search"


# ---------------------------------------------------------------------------
# Parameter building tests
# ---------------------------------------------------------------------------


def test_build_search_params() -> None:
    retriever = AgentDBRetriever(api_key="k", k=5)
    params = retriever._build_search_params("AI news")
    assert params["q"] == "AI news"
    assert params["limit"] == 5


def test_build_latest_params_defaults() -> None:
    retriever = AgentDBRetriever(api_key="k", mode="latest", k=20)
    params = retriever._build_latest_params()
    assert params["limit"] == 20
    assert params["page"] == 1
    assert "content_type" not in params
    assert "tags" not in params


def test_build_latest_params_with_filters() -> None:
    retriever = AgentDBRetriever(
        api_key="k",
        mode="latest",
        content_type="podcast",
        tags="ai,startups",
    )
    params = retriever._build_latest_params()
    assert params["content_type"] == "podcast"
    assert params["tags"] == "ai,startups"


def test_k_capped_at_50_for_search() -> None:
    retriever = AgentDBRetriever(api_key="k", mode="search", k=999)
    params = retriever._build_search_params("test")
    assert params["limit"] == 50


def test_k_capped_at_100_for_latest() -> None:
    retriever = AgentDBRetriever(api_key="k", mode="latest", k=999)
    params = retriever._build_latest_params()
    assert params["limit"] == 100


# ---------------------------------------------------------------------------
# Document conversion tests
# ---------------------------------------------------------------------------


def test_items_to_documents_basic() -> None:
    retriever = AgentDBRetriever(api_key="k")
    docs = retriever._items_to_documents([SAMPLE_ITEM])

    assert len(docs) == 1
    doc = docs[0]
    assert "DeepMind" in doc.page_content
    assert "Key points:" in doc.page_content
    assert "Reward models can be trained" in doc.page_content
    assert doc.metadata["id"] == "abc-123"
    assert doc.metadata["title"] == "AI Safety Breakthrough at DeepMind"
    assert doc.metadata["confidence"] == 0.92
    assert "ai-safety" in doc.metadata["tags"]


def test_items_to_documents_min_confidence_filter() -> None:
    retriever = AgentDBRetriever(api_key="k", min_confidence=0.95)
    docs = retriever._items_to_documents([SAMPLE_ITEM])  # confidence=0.92
    assert len(docs) == 0


def test_items_to_documents_passes_confidence_threshold() -> None:
    retriever = AgentDBRetriever(api_key="k", min_confidence=0.90)
    docs = retriever._items_to_documents([SAMPLE_ITEM])  # confidence=0.92
    assert len(docs) == 1


def test_items_to_documents_missing_body() -> None:
    item = {**SAMPLE_ITEM, "body": None}
    retriever = AgentDBRetriever(api_key="k")
    docs = retriever._items_to_documents([item])
    assert len(docs) == 1
    assert docs[0].metadata["key_points"] == []


def test_items_to_documents_empty_list() -> None:
    retriever = AgentDBRetriever(api_key="k")
    docs = retriever._items_to_documents([])
    assert docs == []


# ---------------------------------------------------------------------------
# Sync retrieval tests (httpx MockTransport)
# ---------------------------------------------------------------------------


def test_get_relevant_documents_search_mode() -> None:
    retriever = AgentDBRetriever(api_key="agentdb-test", mode="search")

    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        docs = retriever._get_relevant_documents("AI safety", run_manager=MagicMock())

    assert len(docs) == 1
    assert docs[0].metadata["title"] == "AI Safety Breakthrough at DeepMind"

    call_kwargs = mock_client.get.call_args
    assert "/search" in call_kwargs[0][0]
    assert call_kwargs[1]["params"]["q"] == "AI safety"


def test_get_relevant_documents_latest_mode() -> None:
    retriever = AgentDBRetriever(
        api_key="agentdb-test", mode="latest", content_type="article"
    )

    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        docs = retriever._get_relevant_documents("", run_manager=MagicMock())

    call_kwargs = mock_client.get.call_args
    assert "/latest" in call_kwargs[0][0]
    assert call_kwargs[1]["params"]["content_type"] == "article"


def test_search_mode_raises_on_empty_query() -> None:
    retriever = AgentDBRetriever(api_key="k", mode="search")
    with pytest.raises(ValueError, match="non-empty query"):
        retriever._get_relevant_documents("   ", run_manager=MagicMock())


def test_http_error_propagates() -> None:
    retriever = AgentDBRetriever(api_key="agentdb-test", mode="latest")

    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            retriever._get_relevant_documents("", run_manager=MagicMock())


# ---------------------------------------------------------------------------
# Async retrieval tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aget_relevant_documents_search_mode() -> None:
    retriever = AgentDBRetriever(api_key="agentdb-test", mode="search")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        docs = await retriever._aget_relevant_documents(
            "AI regulation", run_manager=MagicMock()
        )

    assert len(docs) == 1
    call_kwargs = mock_client.get.call_args
    assert "/search" in call_kwargs[0][0]


@pytest.mark.asyncio
async def test_aget_relevant_documents_latest_mode() -> None:
    retriever = AgentDBRetriever(api_key="agentdb-test", mode="latest")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        docs = await retriever._aget_relevant_documents("", run_manager=MagicMock())

    call_kwargs = mock_client.get.call_args
    assert "/latest" in call_kwargs[0][0]


@pytest.mark.asyncio
async def test_async_search_mode_raises_on_empty_query() -> None:
    retriever = AgentDBRetriever(api_key="k", mode="search")
    with pytest.raises(ValueError, match="non-empty query"):
        await retriever._aget_relevant_documents("", run_manager=MagicMock())
