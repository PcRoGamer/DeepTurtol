"""Tests for the LightRAG benchmark adapter."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from benchmarks.rag_comparison.adapters.base import RAGBenchmark
from benchmarks.rag_comparison.adapters.lightrag_adapter import LightRAGAdapter


# ── Protocol compliance ───────────────────────────────────────────────


def test_protocol_compliance() -> None:
    """LightRAGAdapter satisfies the RAGBenchmark protocol."""
    adapter = LightRAGAdapter()
    assert isinstance(adapter, RAGBenchmark)


# ── Mock-based unit tests ────────────────────────────────────────────


@pytest.fixture()
def adapter() -> LightRAGAdapter:
    return LightRAGAdapter(
        working_dir="/tmp/test_lightrag",
        document_loader=lambda paths: [Path(path).read_text(encoding="utf-8") for path in paths],
    )


@pytest.fixture()
def _mock_lightrag(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch LightRAG so no real LLM/embedding calls are made."""
    mock_rag = MagicMock()
    mock_rag.initialize_storages = AsyncMock()
    mock_rag.ainsert = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="mocked answer")
    mock_rag.finalize_storages = AsyncMock()

    monkeypatch.setattr(
        "benchmarks.rag_comparison.adapters.lightrag_adapter.LightRAG",
        MagicMock(return_value=mock_rag),
    )
    return mock_rag


@pytest.mark.anyio
async def test_index_returns_float(
    adapter: LightRAGAdapter, _mock_lightrag: MagicMock, tmp_path: Path
) -> None:
    """index() must return a float (elapsed seconds) and call ainsert."""
    # Create two temp doc files
    doc1 = tmp_path / "doc1.txt"
    doc2 = tmp_path / "doc2.txt"
    doc1.write_text("Hello world")
    doc2.write_text("Another document")

    await adapter.initialize(str(tmp_path / "working"))

    result = await adapter.index([str(doc1), str(doc2)])

    assert isinstance(result, float)
    assert result >= 0.0
    assert _mock_lightrag.ainsert.call_count == 2


@pytest.mark.anyio
async def test_index_uses_the_configured_document_loader() -> None:
    """Indexing consumes the production parser output, not raw source bytes."""
    parsed = ["# Parsed one", "# Parsed two"]
    loader = MagicMock(return_value=parsed)
    adapter = LightRAGAdapter(document_loader=loader)
    rag = MagicMock()
    rag.ainsert = AsyncMock()
    adapter._rag = rag

    paths = ["first.pdf", "second.pdf"]
    await adapter.index(paths)

    loader.assert_called_once_with(paths)
    assert [call.args[0] for call in rag.ainsert.await_args_list] == parsed


@pytest.mark.anyio
async def test_add_documents_calls_ainsert(
    adapter: LightRAGAdapter, _mock_lightrag: MagicMock, tmp_path: Path
) -> None:
    """add_documents() delegates to ainsert (incremental by design)."""
    doc = tmp_path / "doc.txt"
    doc.write_text("Incremental content")

    await adapter.initialize(str(tmp_path / "working"))
    elapsed = await adapter.add_documents([str(doc)])

    assert isinstance(elapsed, float)
    assert _mock_lightrag.ainsert.call_count == 1


@pytest.mark.anyio
async def test_query_delegates(
    adapter: LightRAGAdapter, _mock_lightrag: MagicMock, tmp_path: Path
) -> None:
    """query() returns the string from aquery."""
    await adapter.initialize(str(tmp_path / "working"))
    answer = await adapter.query("What is RAG?")

    assert answer == "mocked answer"
    _mock_lightrag.aquery.assert_awaited_once()


@pytest.mark.anyio
async def test_query_timed_returns_tuple(
    adapter: LightRAGAdapter, _mock_lightrag: MagicMock, tmp_path: Path
) -> None:
    """query_timed() returns (str, float)."""
    await adapter.initialize(str(tmp_path / "working"))
    result = await adapter.query_timed("What is LightRAG?")

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], float)


@pytest.mark.anyio
async def test_delete_calls_finalize(
    adapter: LightRAGAdapter, _mock_lightrag: MagicMock, tmp_path: Path
) -> None:
    """delete() calls finalize_storages."""
    await adapter.initialize(str(tmp_path / "working"))
    await adapter.delete()

    _mock_lightrag.finalize_storages.assert_awaited_once()


@pytest.mark.anyio
async def test_initialize_creates_working_dir(tmp_path: Path) -> None:
    """initialize() creates the working directory."""
    target = tmp_path / "new_dir"
    adapter = LightRAGAdapter(working_dir=str(target))

    with patch(
        "benchmarks.rag_comparison.adapters.lightrag_adapter.LightRAG"
    ) as MockRAG:
        mock_rag = MagicMock()
        mock_rag.initialize_storages = AsyncMock()
        MockRAG.return_value = mock_rag

        await adapter.initialize()

        assert target.is_dir()
        mock_rag.initialize_storages.assert_awaited_once()
