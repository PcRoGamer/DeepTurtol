"""Native OpenSPG-backed KAG pipeline.  No memory graph or demo corpus is used."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, List, Optional

from deeptutor.runtime.home import get_runtime_data_root
from deeptutor.services.rag.pipelines.base import RetrievalContext
from . import config as kag_config

logger = logging.getLogger(__name__)
DEFAULT_KB_BASE_DIR = str(get_runtime_data_root() / "knowledge_bases")
PROVIDER = "kag"


class KagNotAvailableError(RuntimeError):
    pass


class KagPipeline:
    """Persist chunks and embeddings in OpenSPG, then retrieve with KAG search APIs."""

    def __init__(self, kb_base_dir: Optional[str] = None, **_: Any) -> None:
        self.kb_base_dir = kb_base_dir or DEFAULT_KB_BASE_DIR

    def _ensure_available(self) -> None:
        if not kag_config.is_kag_available():
            raise KagNotAvailableError("KAG is not installed. Install deeptutor[kag].")

    @staticmethod
    def _host() -> str:
        configured = os.getenv("KAG_PROJECT_HOST_ADDR") or os.getenv("OPENS_PG_HOST")
        if configured:
            return configured.rstrip("/")
        if os.name == "nt":
            try:
                output = subprocess.check_output(["wsl.exe", "-d", "Debian", "-u", "root", "--", "hostname", "-I"], text=True, timeout=8)
                match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", output)
                if match:
                    return f"http://{match.group(0)}:8887"
            except (OSError, subprocess.SubprocessError):
                pass
        return "http://127.0.0.1:8887"

    @staticmethod
    def _namespace(kb_name: str) -> str:
        # Neo4j Community supports one database only.  The native deployment therefore has one
        # OpenSPG project (the active DeepTutor knowledge base), rather than pretending that
        # isolated multi-database projects work on this edition.
        if os.getenv("OPENS_PG_COMMUNITY_SINGLE_DATABASE", "true").lower() == "true":
            return "Handbooks"
        cleaned = "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", kb_name) if part) or "KnowledgeBase"
        return f"Dt{cleaned}{hashlib.sha1(kb_name.encode()).hexdigest()[:8]}"

    @staticmethod
    def _model_paths() -> tuple[str, str]:
        local = get_runtime_data_root() / "user" / "models" / "bge-small-en-v1.5"
        if not local.is_dir():
            # Benchmarks and background workers may run below the repository rather than its root.
            local = Path(__file__).resolve().parents[5] / "data" / "user" / "models" / "bge-small-en-v1.5"
        if not local.is_dir():
            raise RuntimeError("Native KAG needs data/user/models/bge-small-en-v1.5.")
        windows_path = str(local)
        wsl_path = "/mnt/" + windows_path[0].lower() + windows_path[2:].replace("\\", "/") if os.name == "nt" else windows_path
        return windows_path, wsl_path

    def _project(self, kb_name: str) -> tuple[int, str, str]:
        from knext.project.client import ProjectClient
        host, namespace = self._host(), self._namespace(kb_name)
        client = ProjectClient(host_addr=host)
        existing_id = (client.get_all() or {}).get(namespace)
        if existing_id is not None:
            return int(existing_id), host, namespace
        _win_model, wsl_model = self._model_paths()
        base_url, model, api_key = kag_config.resolve_kag_llm_settings()
        config = {
            "graph_store": {"type": "neo4j", "uri": "neo4j://127.0.0.1:7687", "user": "neo4j", "password": os.getenv("OPENS_PG_NEO4J_PASSWORD", "openspgNeo4j2026"), "database": "neo4j"},
            "search_engine": {"type": "neo4j", "uri": "neo4j://127.0.0.1:7687", "user": "neo4j", "password": os.getenv("OPENS_PG_NEO4J_PASSWORD", "openspgNeo4j2026"), "database": "neo4j"},
            "vectorizer": {"type": "bge", "path": wsl_model, "vector_dimensions": 384},
            "chat_llm": {"type": "openai", "base_url": base_url, "api_key": api_key, "model": model},
        }
        project = client.create(name=namespace, namespace=namespace, config=config, desc="DeepTutor native KAG")
        schema = f'''namespace {namespace}\n\nChunk(Chunk): EntityType\n  properties:\n    content(Content): Text\n      index: TextAndVector\n    source(Source): Text\n      index: Text\n'''
        from knext.schema.marklang.schema_ml import SPGSchemaMarkLang
        project_id = int(project.id if hasattr(project, "id") else project["id"])
        SPGSchemaMarkLang("", with_server=True, host_addr=host, project_id=project_id, script_data_str=schema).diff_and_sync(False)
        return project_id, host, namespace

    def _index(self, kb_name: str, paths: List[str]) -> bool:
        from deeptutor.services.parsing import ParserError, get_parse_service
        from kag.bridge.spg_server_bridge import init_kag_config
        from kag.builder.component import KGWriter
        from kag.common.vectorize_model.local_bge_model import LocalBGEVectorizeModel
        from kag.interface.common.model.sub_graph import SubGraph
        project_id, host, _namespace = self._project(kb_name)
        model_path, _ = self._model_paths()
        init_kag_config(str(project_id), host)
        vectorizer = LocalBGEVectorizeModel(path=model_path, vector_dimensions=384)
        graph = SubGraph([], [])
        parse_service = get_parse_service()
        for filename in paths:
            path = Path(filename)
            try:
                parsed = parse_service.parse(path)
            except ParserError as exc:
                logger.warning("KAG: parse failed for %s: %s", path.name, exc)
                continue
            text = parsed.markdown.strip() or "\n\n".join(
                str(block.get("text") or block.get("content") or "").strip()
                for block in (parsed.blocks or [])
                if isinstance(block, dict)
            )
            source = path.name
            for offset in range(0, len(text), 1400):
                content = text[offset:offset + 1600]
                if not content.strip():
                    continue
                node_id = hashlib.sha256(f"{source}:{offset}:{content}".encode()).hexdigest()
                graph.add_node(node_id, f"{source} {offset // 1400 + 1}", "Chunk", {"content": content, "source": source, "_content_vector": vectorizer.vectorize(content), "_name_vector": vectorizer.vectorize(source)})
        if graph.nodes:
            KGWriter(project_id=project_id).invoke(graph, write_ckpt=False)
        return True

    async def initialize(self, kb_name: str, file_paths: List[str], **_: Any) -> bool:
        self._ensure_available()
        return await asyncio.to_thread(self._index, kb_name, file_paths)

    async def add_documents(self, kb_name: str, file_paths: List[str], **_: Any) -> bool:
        self._ensure_available()
        return await asyncio.to_thread(self._index, kb_name, file_paths)

    def _search(self, query: str, kb_name: str, mode: str, generate_answer: bool) -> RetrievalContext:
        from kag.bridge.spg_server_bridge import init_kag_config
        from kag.common.tools.search_api.impl.openspg_search_api import OpenSPGSearchAPI
        from kag.common.vectorize_model.local_bge_model import LocalBGEVectorizeModel
        project_id, host, namespace = self._project(kb_name)
        model_path, _ = self._model_paths()
        init_kag_config(str(project_id), host)
        vector = LocalBGEVectorizeModel(path=model_path, vector_dimensions=384).vectorize(query)
        rows = OpenSPGSearchAPI().search_vector(label=f"{namespace}.Chunk", property_key="content", query_vector=vector, topk=4, ef_search=28)
        sources = [{"type": "rag", "kb_name": kb_name, "title": row["node"].get("name", "Chunk"), "content": row["node"].get("content", ""), "score": row.get("score", 0)} for row in rows]
        content = "\n\n".join(item["content"] for item in sources)
        answer = content or "No matching content was found in this knowledge base."
        if generate_answer and content:
            from openai import OpenAI
            base_url, model, api_key = kag_config.resolve_kag_llm_settings()
            completion = OpenAI(base_url=base_url, api_key=api_key).chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": "Answer only from the supplied knowledge-base context. State when the context is insufficient; do not invent facts."},
                    {"role": "user", "content": f"Question: {query}\n\nContext:\n{content}"},
                ],
            )
            answer = completion.choices[0].message.content or answer
        return RetrievalContext(query=query, answer=answer, content=content, provider=PROVIDER, sources=sources, entities=[], relationships=[], reasoning_paths=[], sub_queries=[], intermediate_results=[], communities=[], mode=mode, error_type=None, needs_reindex=False)

    async def search(self, query: str, kb_name: str, **kwargs: Any) -> RetrievalContext:
        self._ensure_available()
        return await asyncio.to_thread(self._search, query, kb_name, kwargs.get("mode", kag_config.DEFAULT_MODE), bool(kwargs.get("generate_answer", False)))

    async def delete(self, kb_name: str, **_: Any) -> bool:
        raise RuntimeError("Native KAG deletion is intentionally disabled in Neo4j Community shared-database mode.")
