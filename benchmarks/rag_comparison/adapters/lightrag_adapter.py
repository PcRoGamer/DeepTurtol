"""LightRAG adapter implementing the RAGBenchmark protocol."""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any

import numpy as np
import openai
from lightrag import LightRAG
from lightrag.base import QueryParam
from lightrag.utils import EmbeddingFunc

logger = logging.getLogger(__name__)


class LightRAGAdapter:
    """Wrap lightrag-hku's LightRAG to satisfy the RAGBenchmark protocol."""

    def __init__(
        self,
        working_dir: str = "./lightrag_benchmark",
        llm_base_url: str = "https://opencode.ai/zen/v1",
        llm_api_key: str = "public",
        llm_model: str = "deepseek-v4-flash-free",
        embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
        embedding_dim: int = 1024,
        document_loader: Callable[[list[str]], list[str]] | None = None,
        **kwargs: Any,
    ) -> None:
        self.working_dir = working_dir
        self.llm_base_url = llm_base_url
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self._rag: LightRAG | None = None
        self._embedder: Any = None
        if document_loader is None:
            from .deeptutor_parser import load_texts

            document_loader = load_texts
        self._document_loader = document_loader
        self._llm_client: Any = None

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def initialize(self, working_dir: str | None = None) -> None:
        """Create working dir, build LightRAG instance, init storages."""
        if working_dir is not None:
            self.working_dir = working_dir
        # A benchmark run must not inherit persisted documents or LLM cache entries
        # from a cancelled prior run.
        if os.path.isdir(self.working_dir):
            shutil.rmtree(self.working_dir)
        os.makedirs(self.working_dir, exist_ok=True)
        logger.info("Initializing LightRAG in %s", self.working_dir)

        # --- LLM client (cloud API) ---
        llm_client = openai.AsyncOpenAI(
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
        )
        self._llm_client = llm_client

        # --- Embedding model (local fastembed-qnn) ---
        def _load_embedder() -> Any:
            from fastembed_qnn import QNNTextEmbedding
            return QNNTextEmbedding(model_name=self.embedding_model)

        logger.info("Loading embedding model %s (one-time ~50s)...", self.embedding_model)
        loop = asyncio.get_running_loop()
        self._embedder = await loop.run_in_executor(None, _load_embedder)
        logger.info("Embedding model ready (dim=%d)", self.embedding_dim)

        async def _llm_func(prompt: str, **kwargs: Any) -> str:
            messages = [{"role": "user", "content": prompt}]
            system_prompt = kwargs.get("system_prompt")
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            extra: dict[str, Any] = {}
            resp_format = kwargs.get("response_format")
            if resp_format:
                extra["response_format"] = resp_format
            resp = await llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                max_tokens=4096,
                **extra,
            )
            content = resp.choices[0].message.content or ""
            return content

        embedder_ref = self._embedder

        async def _embedding_func(texts: list[str]) -> np.ndarray:
            embeddings = await loop.run_in_executor(
                None, lambda: list(embedder_ref.embed(texts))
            )
            return np.array(embeddings, dtype=np.float32)

        self._rag = LightRAG(
            working_dir=self.working_dir,
            llm_model_func=_llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=self.embedding_dim,
                max_token_size=8192,
                func=_embedding_func,
            ),
            entity_extraction_use_json=True,
            chunk_token_size=2000,
            chunk_overlap_token_size=200,
            entity_extract_max_gleaning=0,
            llm_model_max_async=4,
            embedding_func_max_async=2,
            max_parallel_insert=1,
        )
        await self._rag.initialize_storages()
        logger.info("LightRAG storages initialized")

    async def index(self, doc_paths: list[str], label: str = "") -> float:
        """Insert each document into LightRAG. Returns elapsed seconds."""
        assert self._rag is not None, "Call initialize() first"
        t0 = time.perf_counter()
        texts = await asyncio.get_running_loop().run_in_executor(
            None, self._document_loader, doc_paths
        )
        for path, text in zip(doc_paths, texts):
            await asyncio.wait_for(self._rag.ainsert(text, file_paths=[path]), timeout=600)
        elapsed = time.perf_counter() - t0
        logger.info("Indexed %d docs in %.2fs %s", len(doc_paths), elapsed, label)
        return elapsed

    async def add_documents(self, doc_paths: list[str], label: str = "") -> float:
        """Incrementally add documents (same as index for LightRAG)."""
        return await self.index(doc_paths, label=label)

    async def query(self, question: str) -> str:
        assert self._rag is not None, "Call initialize() first"
        # Match KAG exactly: vector retrieval followed by one grounded answer
        # generation call using the same configured OpenCode Zen model.
        context = await self._rag.aquery(
            question,
            param=QueryParam(mode="naive", only_need_context=True, enable_rerank=False, chunk_top_k=4),
        )
        response = await self._llm_client.chat.completions.create(
            model=self.llm_model,
            temperature=0,
            messages=[
                {"role": "system", "content": "Answer only from the supplied knowledge-base context. State when the context is insufficient; do not invent facts."},
                {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"},
            ],
        )
        return response.choices[0].message.content or ""

    async def query_timed(self, question: str) -> tuple[str, float]:
        t0 = time.perf_counter()
        try:
            answer = await asyncio.wait_for(self.query(question), timeout=150)
        except Exception as exc:
            logger.warning("LightRAG benchmark query failed: %s", exc)
            answer = ""
        elapsed = time.perf_counter() - t0
        return answer, elapsed

    def get_index_size(self) -> int:
        """Sum all file sizes in working_dir recursively."""
        total = 0
        for dirpath, _dirnames, filenames in os.walk(self.working_dir):
            for fname in filenames:
                total += os.path.getsize(os.path.join(dirpath, fname))
        return total

    async def delete(self) -> None:
        assert self._rag is not None, "Call initialize() first"
        await self._rag.finalize_storages()
        if os.path.isdir(self.working_dir):
            shutil.rmtree(self.working_dir)
        logger.info("Deleted LightRAG index at %s", self.working_dir)
