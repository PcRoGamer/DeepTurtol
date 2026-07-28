"""Native LazyGraphRAG: build a graph only from vector-search candidates."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
import logging
from pathlib import Path
import re
import shutil
from typing import Any, Callable, Dict, List, Optional

from deeptutor.runtime.home import get_runtime_data_root
from deeptutor.services.rag.index_versioning import resolve_storage_dir_for_rebuild
from deeptutor.services.rag.kb_paths import resolve_kb_dir
from deeptutor.services.rag.pipelines.llamaindex import storage as vector_storage
from deeptutor.services.rag.pipelines.llamaindex.document_loader import LlamaIndexDocumentLoader
from deeptutor.services.rag.pipelines.llamaindex.embedding_adapter import (
    configure_llamaindex_settings,
    set_progress_callback,
    verify_embedding_connectivity,
)

from . import storage

DEFAULT_KB_BASE_DIR = str(get_runtime_data_root() / "knowledge_bases")
_ENTITY_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b")
_STOPWORDS = frozenset({"about", "after", "also", "and", "are", "between", "but", "can", "for", "from", "has", "have", "into", "its", "not", "only", "that", "the", "their", "this", "was", "were", "with", "you"})


class LazyGraphRagPipeline:
    """Vector index at ingest; query-scoped entity co-occurrence graph at search."""

    def __init__(self, kb_base_dir: Optional[str] = None, **_: Any) -> None:
        self.logger = logging.getLogger(__name__)
        self.kb_base_dir = kb_base_dir or DEFAULT_KB_BASE_DIR
        self.document_loader = LlamaIndexDocumentLoader(self.logger)
        configure_llamaindex_settings(self.logger)

    async def initialize(self, kb_name: str, file_paths: List[str], **kwargs: Any) -> bool:
        return await self._index(kb_name, file_paths, replace=True, **kwargs)

    async def add_documents(self, kb_name: str, file_paths: List[str], **kwargs: Any) -> bool:
        return await self._index(kb_name, file_paths, replace=False, **kwargs)

    async def _index(self, kb_name: str, file_paths: List[str], *, replace: bool, **kwargs: Any) -> bool:
        configure_llamaindex_settings(self.logger)
        kb_dir = resolve_kb_dir(self.kb_base_dir, kb_name)
        existing = storage.find_storage(kb_dir)
        root_dir = resolve_storage_dir_for_rebuild(kb_dir, None) if replace or not existing else existing
        callback: Optional[Callable[[int, int, str], None]] = kwargs.get("progress_callback")
        try:
            await verify_embedding_connectivity(self.logger)
            if callback:
                set_progress_callback(callback)
                callback(0, len(file_paths), "Parsing documents for LazyGraphRAG…")
            documents = await self.document_loader.load(file_paths)
            if not documents:
                return False
            loop = asyncio.get_running_loop()
            if existing and not replace:
                await loop.run_in_executor(None, lambda: vector_storage.insert_documents(existing, root_dir, documents))
            else:
                await loop.run_in_executor(None, lambda: vector_storage.create_index(documents, root_dir, show_progress=True))
            storage.write_meta(root_dir)
            if callback:
                callback(len(file_paths), len(file_paths), "LazyGraphRAG index ready")
            return True
        except Exception:
            if (replace or not existing) and root_dir.exists() and not (root_dir / "meta.json").exists():
                shutil.rmtree(root_dir, ignore_errors=True)
            raise
        finally:
            set_progress_callback(None)

    async def search(self, query: str, kb_name: str, **kwargs: Any) -> Dict[str, Any]:
        configure_llamaindex_settings(self.logger)
        root_dir = storage.find_storage(resolve_kb_dir(self.kb_base_dir, kb_name))
        if root_dir is None:
            return {"query": query, "answer": "This LazyGraphRAG knowledge base has no index yet. Add documents before querying.", "content": "", "sources": [], "provider": storage.PROVIDER, "needs_reindex": True}
        try:
            top_k = max(8, int(kwargs.get("top_k") or 5) * 3)
            nodes = await asyncio.get_running_loop().run_in_executor(None, lambda: vector_storage.retrieve_nodes(root_dir, query, top_k=top_k))
            selected, entities, relationships = _lazy_graph_select(query, nodes, limit=int(kwargs.get("top_k") or 5))
            return _nodes_to_result(query, selected, entities, relationships)
        except Exception as exc:
            self.logger.exception("LazyGraphRAG search failed")
            return {"query": query, "answer": str(exc), "content": "", "sources": [], "entities": [], "relationships": [], "reasoning_paths": [], "communities": [], "provider": storage.PROVIDER, "error_type": "retrieval_error"}

    async def delete(self, kb_name: str, **_: Any) -> bool:
        kb_dir = resolve_kb_dir(self.kb_base_dir, kb_name)
        if kb_dir.exists():
            shutil.rmtree(kb_dir)
            return True
        return False


def _entities(text: str) -> set[str]:
    return {term.lower() for term in _ENTITY_RE.findall(text) if term.lower() not in _STOPWORDS}


def _lazy_graph_select(query: str, nodes: list[Any], *, limit: int) -> tuple[list[Any], list[dict[str, Any]], list[dict[str, Any]]]:
    query_entities = _entities(query)
    node_entities = [_entities(str(node.node.text)) for node in nodes]
    edge_weights: Counter[tuple[str, str]] = Counter()
    for terms in node_entities:
        ordered = sorted(terms)[:40]
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                edge_weights[(left, right)] += 1
    neighbors: dict[str, set[str]] = defaultdict(set)
    for left, right in edge_weights:
        neighbors[left].add(right)
        neighbors[right].add(left)
    expanded = set(query_entities)
    for term in query_entities:
        expanded.update(neighbors.get(term, set()))
    ranked = []
    for index, node in enumerate(nodes):
        terms = node_entities[index]
        graph_score = len(terms & expanded) + 2 * len(terms & query_entities)
        ranked.append((-(graph_score + float(node.score or 0)), index, node))
    ranked.sort()
    selected = [item[2] for item in ranked[:limit]]
    entity_counts = Counter(term for terms in node_entities for term in terms)
    entities = [{"title": term, "content": "Entity extracted lazily from retrieved context.", "source": "", "page": "", "chunk_id": term, "score": count} for term, count in entity_counts.most_common(20)]
    relationships = [{"title": f"{left} ↔ {right}", "content": "Co-occurs in retrieved context.", "source": "", "page": "", "chunk_id": f"{left}:{right}", "score": count} for (left, right), count in edge_weights.most_common(30)]
    return selected, entities, relationships


def _nodes_to_result(query: str, nodes: list[Any], entities: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> Dict[str, Any]:
    content_parts, sources = [], []
    for index, node in enumerate(nodes):
        text = str(node.node.text)
        meta = node.node.metadata or {}
        content_parts.append(text)
        sources.append({"title": meta.get("file_name", meta.get("title", f"Document {index + 1}")), "content": text[:200], "source": meta.get("file_path", meta.get("file_name", "")), "page": meta.get("page_label", meta.get("page", "")), "chunk_id": node.node.node_id or str(index), "score": round(node.score, 4) if node.score is not None else ""})
    content = "\n\n".join(content_parts)
    return {"query": query, "answer": content, "content": content, "sources": sources, "entities": entities, "relationships": relationships, "reasoning_paths": [], "communities": [], "provider": storage.PROVIDER}


__all__ = ["LazyGraphRagPipeline"]
