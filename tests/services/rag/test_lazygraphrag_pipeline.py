from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from deeptutor.services.rag.factory import (
    LAZY_GRAPHRAG_PROVIDER,
    get_pipeline,
    list_pipelines,
    normalize_provider_name,
)
from deeptutor.services.rag.index_probe import inspect_provider_index
from deeptutor.services.rag.pipelines.lazygraphrag.pipeline import _lazy_graph_select
from deeptutor.services.rag.pipelines.lazygraphrag.storage import write_meta
from deeptutor.services.rag.service import RAGService


def _node(text: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        node=SimpleNamespace(text=text, metadata={}, node_id=text[:8]),
    )


def test_factory_registers_lazygraphrag() -> None:
    assert normalize_provider_name("LazyGraphRAG") == LAZY_GRAPHRAG_PROVIDER
    assert get_pipeline(LAZY_GRAPHRAG_PROVIDER).__class__.__name__ == "LazyGraphRagPipeline"
    entry = next(item for item in list_pipelines() if item["id"] == LAZY_GRAPHRAG_PROVIDER)
    assert entry["configured"] is True
    assert entry["requires_api_key"] is False


def test_lazy_graph_is_derived_from_query_candidates() -> None:
    nodes = [
        _node("Ada builds a graph retrieval system.", 0.2),
        _node("Graph retrieval connects Ada to documents.", 0.1),
        _node("Cooking recipes are unrelated.", 0.9),
    ]

    selected, entities, relationships = _lazy_graph_select("How does Ada use graph retrieval?", nodes, limit=2)

    assert nodes[0] in selected
    assert any(entity["title"] == "ada" for entity in entities)
    assert any("ada" in relationship["title"] for relationship in relationships)


def test_lazygraphrag_probe_uses_vector_store_artifacts(tmp_path) -> None:
    (tmp_path / "docstore.json").write_text('{"docstore/data": {}}', encoding="utf-8")
    (tmp_path / "index_store.json").write_text("{}", encoding="utf-8")
    write_meta(tmp_path)

    probe = inspect_provider_index(LAZY_GRAPHRAG_PROVIDER, tmp_path)

    assert probe.provider == LAZY_GRAPHRAG_PROVIDER
    assert probe.ready is True


@pytest.mark.asyncio
async def test_service_lifecycle_create_add_search_reindex_and_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the production service path while stubbing only vector I/O.

    This covers factory selection, versioned provider metadata, incremental
    insertion, query-scoped graph construction, a force rebuild, and cleanup
    without requiring a downloaded embedding model in CI.
    """
    from deeptutor.services.rag.pipelines.lazygraphrag import pipeline as lazy_pipeline
    from deeptutor.services.rag.pipelines.lazygraphrag import storage as lazy_storage

    async def no_embedding_probe(_logger) -> None:
        return None

    def write_ready_meta(root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "meta.json").write_text(
            json.dumps(
                {
                    "version": root.name,
                    "provider": LAZY_GRAPHRAG_PROVIDER,
                    "signature": LAZY_GRAPHRAG_PROVIDER,
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ),
            encoding="utf-8",
        )

    def create_index(_documents, root: Path, **_kwargs) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "docstore.json").write_text("{}", encoding="utf-8")
        (root / "index_store.json").write_text("{}", encoding="utf-8")

    def insert_documents(_existing: Path, root: Path, _documents) -> None:
        create_index(_documents, root)

    nodes = [
        _node("Ada Fenwick donated the original telescope to Marlowe Observatory.", 0.9),
        _node("The observatory opened in 1908.", 0.4),
    ]
    monkeypatch.setattr(lazy_pipeline, "verify_embedding_connectivity", no_embedding_probe)
    monkeypatch.setattr(lazy_pipeline.vector_storage, "create_index", create_index)
    monkeypatch.setattr(lazy_pipeline.vector_storage, "insert_documents", insert_documents)
    monkeypatch.setattr(lazy_pipeline.vector_storage, "retrieve_nodes", lambda *_args, **_kwargs: nodes)
    monkeypatch.setattr(lazy_storage, "write_meta", write_ready_meta)

    service = RAGService(kb_base_dir=str(tmp_path), provider=LAZY_GRAPHRAG_PROVIDER)
    pipeline = service._get_pipeline(LAZY_GRAPHRAG_PROVIDER)
    pipeline.document_loader.load = AsyncMock(
        side_effect=[[SimpleNamespace()], [SimpleNamespace()], [SimpleNamespace()]]
    )

    assert await service.initialize("history", ["initial.pdf"])
    assert await service.add_documents("history", ["addition.pdf"])
    result = await service.search("Who donated the Marlowe telescope?", "history")
    assert "Ada Fenwick" in result["answer"]
    assert result["provider"] == LAZY_GRAPHRAG_PROVIDER
    assert result["sources"] and result["entities"] and result["relationships"]

    # ``initialize`` is the public force-reindex operation.
    assert await service.initialize("history", ["initial.pdf", "addition.pdf"])
    assert await service.delete("history")
    assert not (tmp_path / "history").exists()
