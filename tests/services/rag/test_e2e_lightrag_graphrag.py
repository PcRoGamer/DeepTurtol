"""End-to-end tests for LightRAG and GraphRAG pipelines.

Exercises the full RAG lifecycle — initialize → search → add_documents →
search → delete — going through the ``RAGService`` layer exactly as production
does.  Engine adapters (the ``raganything`` / ``graphrag`` imports) are stubbed
at the thinnest seam so the rest of the stack (factory routing, pipeline
orchestration, versioned storage, ingestion, mode resolution) runs for real.

These tests run in CI without LLM keys or optional heavy dependencies.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from deeptutor.services.rag.factory import GRAPHRAG_PROVIDER, LIGHTRAG_PROVIDER
from deeptutor.services.rag.pipelines.graphrag import config as gr_config
from deeptutor.services.rag.pipelines.graphrag import engine as gr_engine
from deeptutor.services.rag.pipelines.graphrag import storage as gr_storage
from deeptutor.services.rag.pipelines.lightrag import config as lr_config
from deeptutor.services.rag.pipelines.lightrag import engine as lr_engine
from deeptutor.services.rag.pipelines.lightrag import storage as lr_storage
from deeptutor.services.rag.service import RAGService

# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


def _write_test_doc(tmp_path: Path, name: str = "notes.txt", content: str = "Shandong province has a pancake.") -> Path:
    """Write a real text file into ``tmp_path`` and return its path."""
    doc = tmp_path / name
    doc.write_text(content, encoding="utf-8")
    return doc


# ---- LightRAG engine stubs ------------------------------------------------


class _FakeLightRag:
    """Minimal stand-in for the RAG-Anything instance ``engine.build_rag`` returns."""

    def __init__(self, working_dir: Path) -> None:
        self.working_dir = Path(working_dir)


def _stub_lightrag(monkeypatch, *, answer: str = "LightRAG answer") -> list[dict]:
    """Patch the LightRAG engine + availability check + parse service.

    Returns a list that accumulates insert call dicts.
    """
    inserts: list[dict] = []

    monkeypatch.setattr(lr_config, "is_lightrag_available", lambda: True)
    monkeypatch.setattr(lr_engine, "build_rag", lambda wd: _FakeLightRag(wd))

    async def fake_insert(rag, content_list, *, file_name, doc_id):
        inserts.append({"file": file_name, "doc_id": doc_id, "blocks": content_list})
        # Write realistic on-disk state so ``storage.has_output`` returns True.
        (rag.working_dir / "vdb_chunks.json").write_text(
            json.dumps({"vectors": [[1.0]]}), encoding="utf-8",
        )
        (rag.working_dir / "kv_store_doc_status.json").write_text(
            json.dumps(
                {
                    doc_id: {
                        "status": "processed",
                        "file_path": file_name,
                        "chunks_list": ["chunk-1"],
                    }
                }
            ),
            encoding="utf-8",
        )

    async def fake_query(rag, question, mode):
        return f"{answer}|{mode}"

    monkeypatch.setattr(lr_engine, "insert", fake_insert)
    monkeypatch.setattr(lr_engine, "query", fake_query)

    # Bypass write_meta's call into the embedding catalog (unconfigured in CI).
    monkeypatch.setattr(lr_storage, "write_meta", lambda root_dir: _fake_write_meta(root_dir, "lightrag"))

    # Stub the parse service so the pipeline can ingest any file without a real parser.
    _stub_parse_service(monkeypatch)

    return inserts


# ---- GraphRAG engine stubs -------------------------------------------------


class _Cfg:
    """Minimal config stand-in for ``build_settings`` / ``write_settings``."""

    def __init__(self, model: str, url: str, key: str, dim: int = 3072):
        self.model = model
        self.effective_url = url
        self.base_url = None
        self.api_key = key
        self.dim = dim


def _stub_graphrag(monkeypatch, *, answer: str = "GraphRAG answer") -> list[dict]:
    """Patch the GraphRAG engine + availability check + model configs.

    Returns a list that accumulates ``engine.build`` call dicts.
    """
    builds: list[dict] = []

    monkeypatch.setattr(gr_config, "is_graphrag_available", lambda: True)

    async def fake_build(root_dir, *, is_update=False):
        builds.append({"root": str(root_dir), "is_update": is_update})
        # Write a parquet stub so ``storage.has_output`` returns True.
        out = gr_storage.output_dir(Path(root_dir))
        out.mkdir(parents=True, exist_ok=True)
        (out / "entities.parquet").write_bytes(b"")

    async def fake_search(root_dir, query, mode):
        return f"{answer}|{mode}", {"sources": [{"id": "u1", "text": "grounded context"}]}

    monkeypatch.setattr(gr_engine, "build", fake_build)
    monkeypatch.setattr(gr_engine, "search", fake_search)

    # Inject fake model configs so write_settings() succeeds without a real catalog.
    monkeypatch.setattr(
        "deeptutor.services.config.resolve_llm_runtime_config",
        lambda: _Cfg("gpt-4o-mini", "https://llm.test/v1", "sk-llm"),
    )
    monkeypatch.setattr(
        "deeptutor.services.embedding.get_embedding_config",
        lambda: _Cfg("emb-model", "https://emb.test/v1", "sk-emb"),
    )

    # Bypass write_meta's call into the embedding catalog.
    monkeypatch.setattr(gr_storage, "write_meta", lambda root_dir: _fake_write_meta(root_dir, "graphrag"))

    return builds


# ---- common stubs ----------------------------------------------------------


def _fake_write_meta(root_dir: Path, provider: str) -> None:
    """Write a minimal ``meta.json`` without reaching into the embedding catalog."""
    from deeptutor.services.file_io import atomic_write_json

    target = Path(root_dir)
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": target.name,
        "signature": provider,
        "provider": provider,
        "layout": "flat",
        "created_at": "2026-01-01T00:00:00Z",
    }
    atomic_write_json(target / "meta.json", payload)


def _stub_parse_service(monkeypatch) -> None:
    """Stub the parse service so LightRAG ingestion succeeds."""
    from deeptutor.services.parsing.types import ParsedDocument

    class _Service:
        def parse(self, path, **_):
            text = Path(path).read_text(encoding="utf-8")
            return ParsedDocument(
                markdown=text,
                blocks=[{"type": "text", "text": text, "page_idx": 0}] if text.strip() else [],
                source_hash="h_" + Path(path).stem,
                engine="fake",
            )

    monkeypatch.setattr("deeptutor.services.parsing.get_parse_service", lambda: _Service())


def _bind_provider(tmp_path: Path, kb_name: str, provider: str) -> None:
    """Write a ``kb_config.json`` so ``resolve_bound_provider`` finds ``provider``."""
    config_path = tmp_path / "kb_config.json"
    data: dict = {}
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
    kbs = data.setdefault("knowledge_bases", {})
    kbs.setdefault(kb_name, {})["rag_provider"] = provider
    config_path.write_text(json.dumps(data), encoding="utf-8")


# =========================================================================== #
# LightRAG E2E
# =========================================================================== #


class TestLightRAGE2E:
    """End-to-end lifecycle tests for the LightRAG provider."""

    def test_initialize_search_delete(self, tmp_path, monkeypatch) -> None:
        """Full lifecycle: init → search → delete."""
        inserts = _stub_lightrag(monkeypatch)
        doc = _write_test_doc(tmp_path)

        svc = RAGService(kb_base_dir=str(tmp_path), provider=LIGHTRAG_PROVIDER)

        # --- initialize ---
        ok = asyncio.run(svc.initialize("kb", [str(doc)]))
        assert ok is True
        assert len(inserts) == 1
        assert inserts[0]["file"] == "notes.txt"

        # --- search ---
        _bind_provider(tmp_path, "kb", LIGHTRAG_PROVIDER)
        result = asyncio.run(svc.search("What does Shandong have?", "kb"))
        assert "LightRAG answer" in result["answer"]
        assert result["provider"] == LIGHTRAG_PROVIDER

        # --- delete ---
        ok = asyncio.run(svc.delete("kb"))
        assert ok is True
        assert not (tmp_path / "kb").exists()

    def test_add_documents_extends_index(self, tmp_path, monkeypatch) -> None:
        """Adding docs after init runs a second insert."""
        inserts = _stub_lightrag(monkeypatch)
        doc1 = _write_test_doc(tmp_path, "a.txt", "first document")
        doc2 = _write_test_doc(tmp_path, "b.txt", "second document")

        svc = RAGService(kb_base_dir=str(tmp_path), provider=LIGHTRAG_PROVIDER)
        asyncio.run(svc.initialize("kb", [str(doc1)]))
        assert len(inserts) == 1

        ok = asyncio.run(svc.add_documents("kb", [str(doc2)]))
        assert ok is True
        assert len(inserts) == 2
        assert inserts[1]["file"] == "b.txt"

    def test_search_mode_override(self, tmp_path, monkeypatch) -> None:
        """An explicit mode kwarg propagates through the stack."""
        _stub_lightrag(monkeypatch)
        doc = _write_test_doc(tmp_path)

        svc = RAGService(kb_base_dir=str(tmp_path), provider=LIGHTRAG_PROVIDER)
        asyncio.run(svc.initialize("kb", [str(doc)]))

        _bind_provider(tmp_path, "kb", LIGHTRAG_PROVIDER)
        result = asyncio.run(svc.search("q", "kb", mode="global"))
        assert result["answer"].endswith("|global")

    def test_empty_doc_returns_false(self, tmp_path, monkeypatch) -> None:
        """Initializing with an empty document returns False."""
        _stub_lightrag(monkeypatch)
        doc = _write_test_doc(tmp_path, "empty.txt", "")

        svc = RAGService(kb_base_dir=str(tmp_path), provider=LIGHTRAG_PROVIDER)
        ok = asyncio.run(svc.initialize("kb", [str(doc)]))
        assert ok is False


# =========================================================================== #
# GraphRAG E2E
# =========================================================================== #


class TestGraphRAGE2E:
    """End-to-end lifecycle tests for the GraphRAG provider."""

    def test_initialize_search_delete(self, tmp_path, monkeypatch) -> None:
        """Full lifecycle: init → search → delete."""
        builds = _stub_graphrag(monkeypatch)
        doc = _write_test_doc(tmp_path)

        svc = RAGService(kb_base_dir=str(tmp_path), provider=GRAPHRAG_PROVIDER)

        # --- initialize ---
        ok = asyncio.run(svc.initialize("kb", [str(doc)]))
        assert ok is True
        assert len(builds) == 1
        assert builds[0]["is_update"] is False

        # --- search ---
        _bind_provider(tmp_path, "kb", GRAPHRAG_PROVIDER)
        result = asyncio.run(svc.search("What does Shandong have?", "kb"))
        assert "GraphRAG answer" in result["answer"]
        assert result["provider"] == GRAPHRAG_PROVIDER
        assert isinstance(result.get("sources"), list)

        # --- delete ---
        ok = asyncio.run(svc.delete("kb"))
        assert ok is True
        assert not (tmp_path / "kb").exists()

    def test_add_documents_runs_update(self, tmp_path, monkeypatch) -> None:
        """Adding docs to an existing index passes ``is_update=True``."""
        builds = _stub_graphrag(monkeypatch)
        doc1 = _write_test_doc(tmp_path, "a.txt", "first document")
        doc2 = _write_test_doc(tmp_path, "b.txt", "second document")

        svc = RAGService(kb_base_dir=str(tmp_path), provider=GRAPHRAG_PROVIDER)
        asyncio.run(svc.initialize("kb", [str(doc1)]))
        assert builds[0]["is_update"] is False

        ok = asyncio.run(svc.add_documents("kb", [str(doc2)]))
        assert ok is True
        assert builds[-1]["is_update"] is True

    def test_search_mode_from_kb_config(self, tmp_path, monkeypatch) -> None:
        """Per-KB ``search_mode`` in ``kb_config.json`` propagates to the engine."""
        _stub_graphrag(monkeypatch)
        doc = _write_test_doc(tmp_path)

        svc = RAGService(kb_base_dir=str(tmp_path), provider=GRAPHRAG_PROVIDER)
        asyncio.run(svc.initialize("kb", [str(doc)]))

        # Write a per-KB search_mode.
        config_path = tmp_path / "kb_config.json"
        data = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        kbs = data.setdefault("knowledge_bases", {})
        kbs.setdefault("kb", {}).update({"search_mode": "global", "rag_provider": GRAPHRAG_PROVIDER})
        config_path.write_text(json.dumps(data), encoding="utf-8")

        result = asyncio.run(svc.search("q", "kb"))
        assert result["answer"].endswith("|global")

    def test_empty_doc_returns_false(self, tmp_path, monkeypatch) -> None:
        """Initializing with an empty/image-only document returns False."""
        _stub_graphrag(monkeypatch)
        img = tmp_path / "pic.png"
        img.write_bytes(b"\x89PNG")

        svc = RAGService(kb_base_dir=str(tmp_path), provider=GRAPHRAG_PROVIDER)
        ok = asyncio.run(svc.initialize("kb", [str(img)]))
        assert ok is False
