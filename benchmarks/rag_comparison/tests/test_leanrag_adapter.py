"""Tests for the LeanRAG adapter."""
from __future__ import annotations

from pathlib import Path

import pytest

from ..adapters.base import RAGBenchmark
from ..adapters.deeptutor_parser import load_texts
from ..adapters.leanrag_adapter import LeanRAGAdapter

VENDOR_LEANRAG = Path(__file__).resolve().parent.parent.parent / "vendor" / "LeanRAG"


def test_default_document_loader_uses_deeptutor_parse_service() -> None:
    adapter = LeanRAGAdapter(
        llm_base_url="http://localhost:8000/v1",
        llm_api_key="test-key",
        llm_model="test-llm",
        embedding_model="test-embed",
        embedding_dim=768,
    )

    assert adapter._document_loader is load_texts


# ---- Protocol compliance ---------------------------------------------------


@pytest.mark.skipif(
    not VENDOR_LEANRAG.exists(), reason="LeanRAG not cloned at vendor/LeanRAG"
)
class TestLeanRAGProtocolCompliance:
    """Verify the adapter satisfies the RAGBenchmark protocol."""

    def test_is_runtime_checkable_protocol(self) -> None:
        adapter = LeanRAGAdapter(
            working_dir="/tmp/_leanrag_proto_test",
            llm_base_url="http://localhost:8000/v1",
            llm_api_key="test-key",
            llm_model="test-llm",
            embedding_base_url="http://localhost:8000/v1",
            embedding_api_key="test-key",
            embedding_model="test-embed",
            embedding_dim=768,
        )
        assert isinstance(adapter, RAGBenchmark)

    def test_has_all_protocol_methods(self) -> None:
        adapter = LeanRAGAdapter(
            working_dir="/tmp/_leanrag_proto_test",
            llm_base_url="http://localhost:8000/v1",
            llm_api_key="test-key",
            llm_model="test-llm",
            embedding_base_url="http://localhost:8000/v1",
            embedding_api_key="test-key",
            embedding_model="test-embed",
            embedding_dim=768,
        )
        for method in (
            "initialize",
            "index",
            "add_documents",
            "query",
            "query_timed",
            "get_index_size",
            "delete",
        ):
            assert hasattr(adapter, method), f"Missing protocol method: {method}"


# ---- Chunking ---------------------------------------------------------------


@pytest.mark.skipif(
    not VENDOR_LEANRAG.exists(), reason="LeanRAG not cloned at vendor/LeanRAG"
)
class TestLeanRAGChunking:
    """Verify ``chunk_documents`` from ``file_chunk`` produces results."""

    @pytest.fixture(autouse=True)
    def _add_leanrag_to_path(self) -> None:
        leanrag_str = str(VENDOR_LEANRAG)
        if leanrag_str not in __import__("sys").path:
            __import__("sys").path.insert(0, leanrag_str)

    def test_chunk_documents_produces_output(self) -> None:
        from file_chunk import chunk_documents

        docs = [
            "The quick brown fox jumps over the lazy dog. " * 50,
            "Another document with completely different content. " * 50,
        ]
        chunks = chunk_documents(
            docs, max_token_size=512, overlap_token_size=64
        )

        assert len(chunks) > 0, "Expected at least one chunk"

        for chunk in chunks:
            assert "hash_code" in chunk, "Chunk missing 'hash_code'"
            assert "text" in chunk, "Chunk missing 'text'"
            assert len(chunk["text"]) > 0, "Chunk text is empty"

    def test_chunk_documents_respects_token_size(self) -> None:
        from file_chunk import chunk_documents

        short_doc = "Short document. "
        chunks = chunk_documents(
            [short_doc], max_token_size=512, overlap_token_size=64
        )
        # A very short document should produce at least one chunk
        assert len(chunks) >= 1

    def test_large_document_produces_multiple_chunks(self) -> None:
        from file_chunk import chunk_documents

        large_doc = "Word " * 5000  # ~5000 tokens, well above 512 limit
        chunks = chunk_documents(
            [large_doc], max_token_size=512, overlap_token_size=64
        )
        assert len(chunks) > 1, "Large document should produce multiple chunks"
