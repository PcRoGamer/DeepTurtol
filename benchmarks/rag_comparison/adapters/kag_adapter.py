"""Adapter for the native DeepTutor/OpenSPG KAG deployment.

This deliberately benchmarks persisted KAG vector retrieval, not a mock solver or
an in-process memory graph.  Responses are the retrieved grounded passages.
"""
from __future__ import annotations

import asyncio
import base64
import os
import subprocess
import time
from pathlib import Path

from deeptutor.services.rag.pipelines.kag.pipeline import KagPipeline


class KAGAdapter:
    def __init__(self, kb_name: str = "benchmark_kag") -> None:
        self.kb_name = kb_name
        self.pipeline = KagPipeline()

    async def initialize(self, working_dir: str | None = None) -> None:
        # Community Neo4j uses one physical database, but benchmark data still
        # gets its own OpenSPG namespace and Neo4j indexes.
        os.environ["OPENS_PG_COMMUNITY_SINGLE_DATABASE"] = "false"
        await asyncio.to_thread(self.pipeline._project, self.kb_name)
        await self._ensure_indexes()
        await self._clear_native_chunks()

    async def _ensure_indexes(self) -> None:
        namespace = self.pipeline._namespace(self.kb_name)
        safe = namespace.lower()
        query = (
            f"CREATE VECTOR INDEX {safe}_chunk_content_vector IF NOT EXISTS FOR (n:`{namespace}.Chunk`) ON (n._content_vector) "
            'OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: "cosine"}}; '
            f"CREATE VECTOR INDEX {safe}_chunk_name_vector IF NOT EXISTS FOR (n:`{namespace}.Chunk`) ON (n._name_vector) "
            'OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: "cosine"}}; '
        )
        await self._run_cypher(query)

    async def _run_cypher(self, query: str) -> None:
        encoded = base64.b64encode((
            "/opt/deeptutor/services/neo4j/bin/cypher-shell "
            "-a bolt://127.0.0.1:7687 -u neo4j -p 'openspgNeo4j2026' "
            f"'{query}'"
        ).encode("utf-8")).decode("ascii")
        await asyncio.to_thread(
            subprocess.run,
            ["wsl.exe", "-d", "Debian", "-u", "root", "--", "bash", "-lc", f"echo {encoded} | base64 -d | bash"],
            check=True, capture_output=True, text=True,
        )

    async def _clear_native_chunks(self) -> None:
        """Clear only benchmark Chunk nodes from the shared Community database."""
        if os.name != "nt":
            raise RuntimeError("The configured native KAG benchmark requires the WSL2 deployment.")
        namespace = self.pipeline._namespace(self.kb_name)
        await self._run_cypher(f"MATCH (n:`{namespace}.Chunk`) DETACH DELETE n;")

    async def index(self, doc_paths: list[str], label: str = "") -> float:
        start = time.perf_counter()
        await self.pipeline.initialize(self.kb_name, doc_paths)
        return time.perf_counter() - start

    async def add_documents(self, doc_paths: list[str], label: str = "") -> float:
        start = time.perf_counter()
        await self.pipeline.add_documents(self.kb_name, doc_paths)
        return time.perf_counter() - start

    async def query(self, question: str) -> str:
        result = await self.pipeline.search(question, self.kb_name, generate_answer=True)
        return str(result.get("answer", ""))

    async def query_timed(self, question: str) -> tuple[str, float]:
        start = time.perf_counter()
        answer = await self.query(question)
        return answer, time.perf_counter() - start

    def get_index_size(self) -> int:
        # The graph is shared by Neo4j Community; node count is not a byte-size metric.
        return 0

    async def delete(self) -> None:
        await self._clear_native_chunks()
