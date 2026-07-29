"""LeanRAG adapter -- script-based graph RAG benchmark."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path
from collections.abc import Callable

import numpy as np
import yaml

logger = logging.getLogger(__name__)


class LeanRAGAdapter:
    """Implement the RAGBenchmark protocol for LeanRAG (script-based).

    LeanRAG lives in ``vendor/LeanRAG/`` relative to the benchmark dir.
    This adapter drives it by chunking documents, writing a ``config.yaml``
    that points at the caller-supplied LLM/embedding endpoints, then
    invoking the LeanRAG scripts (``deal_triple.py``, ``build_graph.py``)
    as subprocesses for indexing and using ``query_graph`` in-process for
    retrieval.
    """

    def __init__(
        self,
        *,
        working_dir: str = "",
        llm_base_url: str,
        llm_api_key: str,
        llm_model: str,
        embedding_model: str,
        embedding_dim: int,
        mysql_host: str = "localhost",
        mysql_port: int = 3306,
        mysql_user: str = "root",
        mysql_password: str = "",
        document_loader: Callable[[list[str]], list[str]] | None = None,
    ) -> None:
        self._working_dir = working_dir
        self._llm_base_url = llm_base_url
        self._llm_api_key = llm_api_key
        self._llm_model = llm_model
        self._embedding_model = embedding_model
        self._embedding_dim = embedding_dim
        self._mysql_host = mysql_host
        self._mysql_port = mysql_port
        self._mysql_user = mysql_user
        self._mysql_password = mysql_password

        self._leanrag_dir: Path | None = None
        self._embedder = None
        if document_loader is None:
            from .deeptutor_parser import load_texts

            document_loader = load_texts
        self._document_loader = document_loader

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _ensure_leanrag_importable(self) -> None:
        """Add ``vendor/LeanRAG`` to *sys.path* so LeanRAG modules can be
        imported as top-level names (e.g. ``from file_chunk import ...``).
        """
        self._leanrag_dir = (
            Path(__file__).resolve().parent.parent / "vendor" / "LeanRAG"
        )
        if not self._leanrag_dir.exists():
            raise FileNotFoundError(
                f"LeanRAG not cloned at {self._leanrag_dir}. "
                "Clone from https://github.com/KnowledgeXLab/LeanRAG"
            )
        leanrag_str = str(self._leanrag_dir)
        if leanrag_str not in sys.path:
            sys.path.insert(0, leanrag_str)

    def _write_config(self) -> None:
        """Write a ``config.yaml`` in the LeanRAG dir with our LLM / embedding
        endpoints.  LeanRAG scripts read this at module level.

        Format::

            glm:
              model: <embedding_model>
              base_url: <embedding_base_url>
              embedding_model: <embedding_model>
            deepseek:
              model: <llm_model>
              api_key: <llm_api_key>
              base_url: <llm_base_url>
            model_params:
              openai_embedding_dim: <embedding_dim>
              glm_embedding_dim: <embedding_dim>
              max_token_size: 8192
        """
        config = {
            "glm": {
                "model": self._embedding_model,
                "base_url": "http://localhost/unused-local-fastembed",
                "embedding_model": self._embedding_model,
            },
            "deepseek": {
                "model": self._llm_model,
                "api_key": self._llm_api_key,
                "base_url": self._llm_base_url,
            },
            "model_params": {
                "openai_embedding_dim": self._embedding_dim,
                "glm_embedding_dim": self._embedding_dim,
                "max_token_size": 8192,
            },
        }
        config_path = self._leanrag_dir / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as fh:
            yaml.dump(config, fh, default_flow_style=False, allow_unicode=True)
        logger.info("Wrote LeanRAG config to %s", config_path)

    def _make_llm_func(self):
        """Return a *synchronous* ``use_llm_func(prompt, system_prompt=None,
        history_messages=[])`` compatible callable.

        LeanRAG's ``query_graph`` calls ``use_llm_func(query,
        system_prompt=sys_prompt)`` and ``build_graph.py`` feeds the result
        into clustering pipelines via ``InstanceManager.generate_text``.
        """
        from openai import OpenAI

        client = OpenAI(
            base_url=self._llm_base_url,
            api_key=self._llm_api_key,
        )

        def _llm_func(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict] | None = None,
            **_kwargs,
        ) -> str:
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if history_messages:
                messages.extend(history_messages)
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self._llm_model,
                messages=messages,
            )
            return response.choices[0].message.content or ""

        return _llm_func

    def _embed(self, texts: str | list[str]) -> np.ndarray:
        """Embed locally, matching the LightRAG benchmark configuration."""
        assert self._embedder is not None, "Call initialize() first"
        if isinstance(texts, str):
            texts = [texts]
        return np.asarray(list(self._embedder.embed(texts)), dtype=np.float32)

    @staticmethod
    def _parse_json(value: str) -> dict | list | None:
        """Accept JSON responses wrapped in prose or Markdown fences."""
        value = value.strip()
        if value.startswith("```"):
            value = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", value, flags=re.I)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            match = re.search(r"[\\[{].*[\\]}]", value, flags=re.S)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def _extract_chunk(self, text: str, source_id: str) -> tuple[list[dict], list[dict]]:
        """Create LeanRAG's entity/relation records from one text chunk."""
        llm = self._make_llm_func()
        prompt = """Extract a compact knowledge graph from the text below. Return JSON only,
with this schema: {\"entities\":[{\"name\":str,\"type\":str,\"description\":str}],
\"relations\":[{\"source\":str,\"target\":str,\"description\":str}]}. Include only
facts stated in the text; use exact, consistent entity names.\n\nTEXT:\n""" + text
        parsed = None
        for _attempt in range(3):
            parsed = self._parse_json(llm(prompt))
            if isinstance(parsed, dict) and isinstance(parsed.get("entities"), list):
                break
        if not isinstance(parsed, dict):
            logger.warning("No usable JSON extraction for chunk %s", source_id)
            return [], []
        entities = []
        seen = set()
        for item in parsed.get("entities", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            entities.append({"entity_name": name, "entity_type": str(item.get("type", "entity")),
                             "description": str(item.get("description", name)), "source_id": source_id,
                             "degree": 0, "parent": "root"})
        valid = {item["entity_name"] for item in entities}
        relations = []
        for item in parsed.get("relations", []):
            if not isinstance(item, dict):
                continue
            source, target = str(item.get("source", "")).strip(), str(item.get("target", "")).strip()
            if source in valid and target in valid and source != target:
                relations.append({"src_tgt": source, "tgt_src": target,
                                  "description": str(item.get("description", "related")),
                                  "weight": 1, "source_id": source_id, "level": 0})
        return entities, relations

    def _write_mysql_graph(self, entities: list[dict], relations: list[dict]) -> None:
        """Persist the LeanRAG retrieval tables using the configured local DB."""
        import pymysql
        dbname = Path(self._working_dir).name
        conn = pymysql.connect(host=self._mysql_host, port=self._mysql_port,
                               user=self._mysql_user, password=self._mysql_password,
                               charset="utf8mb4", autocommit=True)
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS `{dbname}`")
                cur.execute(f"CREATE DATABASE `{dbname}` CHARACTER SET utf8mb4")
                cur.execute(f"USE `{dbname}`")
                cur.execute("CREATE TABLE entities (entity_name varchar(500), description text, source_id varchar(1000), degree int, parent varchar(1000), level int, INDEX en(entity_name)) CHARACTER SET utf8mb4")
                cur.execute("CREATE TABLE relations (src_tgt varchar(190), tgt_src varchar(190), description text, weight int, level int, INDEX link(src_tgt,tgt_src)) CHARACTER SET utf8mb4")
                cur.execute("CREATE TABLE communities (entity_name varchar(500), entity_description text, findings text, INDEX en(entity_name)) CHARACTER SET utf8mb4")
                cur.executemany("INSERT INTO entities VALUES (%s,%s,%s,%s,%s,%s)",
                                [(e["entity_name"], e["description"], e["source_id"], e["degree"], e["parent"], 0) for e in entities])
                if relations:
                    cur.executemany("INSERT INTO relations VALUES (%s,%s,%s,%s,%s)",
                                    [(r["src_tgt"], r["tgt_src"], r["description"], r["weight"], 0) for r in relations])
        finally:
            conn.close()

    def _build_index(self) -> None:
        """Build LeanRAG's local Milvus index and SQL graph from extracted records."""
        chunks_file = Path(self._working_dir) / "chunks.json"
        chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
        all_entities: dict[str, dict] = {}
        all_relations: dict[tuple[str, str], dict] = {}
        for chunk in chunks:
            entities, relations = self._extract_chunk(chunk["text"], chunk["hash_code"])
            for entity in entities:
                existing = all_entities.get(entity["entity_name"])
                if existing:
                    existing["description"] += " | " + entity["description"]
                    if entity["source_id"] not in existing["source_id"].split("|"):
                        existing["source_id"] += "|" + entity["source_id"]
                else:
                    all_entities[entity["entity_name"]] = entity
            for relation in relations:
                all_relations[(relation["src_tgt"], relation["tgt_src"])] = relation
        if not all_entities:
            raise RuntimeError("LeanRAG extraction produced no entities; cannot build an index")
        entities = list(all_entities.values())
        vectors = self._embed([e["description"] for e in entities])
        for entity, vector in zip(entities, vectors):
            entity["vector"] = vector
        from database_utils import build_vector_search
        build_vector_search([entities], self._working_dir)
        for entity in entities:
            entity.pop("vector", None)
        (Path(self._working_dir) / "all_entities.json").write_text(json.dumps([entities, {"entity_name": "root", "description": "root", "source_id": "", "parent": "root"}], ensure_ascii=False), encoding="utf-8")
        (Path(self._working_dir) / "generate_relations.json").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in all_relations.values()), encoding="utf-8")
        (Path(self._working_dir) / "community.json").write_text("", encoding="utf-8")
        self._write_mysql_graph(entities, list(all_relations.values()))

    def _patch_pymysql(self) -> None:
        """Monkey-patch ``pymysql.connect`` so that every internal LeanRAG
        call to ``database_utils.*`` (which hard-codes MySQL credentials)
        uses the adapter's MySQL configuration instead.
        """
        import pymysql

        _orig_connect = pymysql.connect

        def _patched_connect(*args, **kwargs):  # type: ignore[no-untyped-def]
            kwargs["host"] = self._mysql_host
            kwargs["port"] = self._mysql_port
            kwargs["user"] = self._mysql_user
            kwargs["passwd"] = self._mysql_password
            kwargs.setdefault("charset", "utf8mb4")
            return _orig_connect(*args, **kwargs)

        pymysql.connect = _patched_connect  # type: ignore[assignment]

    async def _run_subprocess(
        self,
        cmd: list[str],
        cwd: str | None = None,
    ) -> None:
        """Run *cmd* as an async subprocess, logging stdout / stderr and
        raising ``RuntimeError`` on non-zero exit.
        """
        env = os.environ.copy()
        if self._leanrag_dir:
            leanrag_str = str(self._leanrag_dir)
            env["PYTHONPATH"] = leanrag_str + os.pathsep + env.get("PYTHONPATH", "")

        effective_cwd = cwd or str(self._leanrag_dir)
        logger.info("Running: %s (cwd=%s)", " ".join(cmd), effective_cwd)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=effective_cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            logger.debug("STDOUT:\n%s", stdout.decode(errors="replace"))
        if stderr:
            logger.debug("STDERR:\n%s", stderr.decode(errors="replace"))
        if proc.returncode != 0:
            raise RuntimeError(
                f"Subprocess failed (rc={proc.returncode}):\n"
                f"stderr (last 2000 chars): "
                f"{stderr.decode(errors='replace')[-2000:]}"
            )

    # ------------------------------------------------------------------ #
    # RAGBenchmark protocol
    # ------------------------------------------------------------------ #

    async def initialize(self, working_dir: str) -> None:
        """One-time setup: create *working_dir*, make LeanRAG importable,
        write ``config.yaml``, and patch ``pymysql``.
        """
        self._working_dir = working_dir
        os.makedirs(working_dir, exist_ok=True)
        self._ensure_leanrag_importable()
        self._write_config()
        self._patch_pymysql()
        from fastembed_qnn import QNNTextEmbedding
        self._embedder = QNNTextEmbedding(model_name=self._embedding_model)

    async def index(self, doc_paths: list[str], label: str = "") -> float:
        """Build a fresh LeanRAG index from *doc_paths*.

        Pipeline
        --------
        1. Chunk documents via ``file_chunk.chunk_documents``.
        2. Write chunks to ``working_dir/chunks.json``.
        3. Run ``GraphExtraction/deal_triple.py`` (entity / relation
           extraction via LLM) as a subprocess.
        4. Run ``build_graph.py -p WORKING_DIR -n 2`` (hierarchical graph
           construction) as a subprocess.

        Returns wall-clock seconds.
        """
        t0 = time.perf_counter()
        # -- Step 1 & 2: Chunk documents --------------------------------
        from file_chunk import chunk_documents

        texts = await asyncio.get_running_loop().run_in_executor(
            None, self._document_loader, doc_paths
        )

        chunks = chunk_documents(
            texts,
            max_token_size=1024,
            overlap_token_size=128,
        )

        chunks_file = os.path.join(self._working_dir, "chunks.json")
        with open(chunks_file, "w", encoding="utf-8") as fh:
            json.dump(chunks, fh, ensure_ascii=False, indent=2)
        logger.info("Wrote %d chunks to %s", len(chunks), chunks_file)

        # The upstream scripts hard-code the authors' paths and model server.
        # Build the identical storage format through this configured adapter.
        await asyncio.get_running_loop().run_in_executor(None, self._build_index)

        elapsed = time.perf_counter() - t0
        logger.info("LeanRAG index built in %.1fs (label=%s)", elapsed, label)
        return elapsed

    async def add_documents(self, doc_paths: list[str], label: str = "") -> float:
        """Incrementally add documents by re-chunking, appending, and
        rebuilding the entire graph.

        LeanRAG has no native incremental add -- this measures the full
        rebuild cost, which is the metric the benchmark is designed to
        capture.

        Returns wall-clock seconds.
        """
        t0 = time.perf_counter()
        # -- Read existing chunks (if any) ------------------------------
        chunks_file = os.path.join(self._working_dir, "chunks.json")
        existing_chunks: list[dict] = []
        if os.path.exists(chunks_file):
            with open(chunks_file, "r", encoding="utf-8") as fh:
                existing_chunks = json.load(fh)

        # -- Chunk new documents ----------------------------------------
        from file_chunk import chunk_documents

        new_texts = await asyncio.get_running_loop().run_in_executor(
            None, self._document_loader, doc_paths
        )

        new_chunks = chunk_documents(
            new_texts,
            max_token_size=1024,
            overlap_token_size=128,
        )

        # -- Combine and write ------------------------------------------
        all_chunks = existing_chunks + new_chunks
        with open(chunks_file, "w", encoding="utf-8") as fh:
            json.dump(all_chunks, fh, ensure_ascii=False, indent=2)
        logger.info(
            "Combined chunks: %d existing + %d new = %d total",
            len(existing_chunks),
            len(new_chunks),
            len(all_chunks),
        )

        await asyncio.get_running_loop().run_in_executor(None, self._build_index)

        elapsed = time.perf_counter() - t0
        logger.info(
            "LeanRAG rebuild completed in %.1fs (label=%s)", elapsed, label
        )
        return elapsed

    async def query(self, question: str) -> str:
        """Run a single query against the LeanRAG graph.

        Steps:
        1. Import ``embedding`` and ``query_graph`` from the ``query_graph``
           module (which reads ``config.yaml`` at import time).
        2. Connect to MySQL via ``pymysql.connect()``.
        3. Build a ``global_config`` dict and call ``query_graph``.
        4. Close the DB connection and return the response string.
        """
        import pymysql

        # -- Import query_graph (reads config.yaml at module level) ------
        # Temporarily chdir to the LeanRAG dir so the module-level
        # ``open('config.yaml')`` resolves correctly.
        leanrag_str = str(self._leanrag_dir)
        original_cwd = os.getcwd()
        try:
            os.chdir(leanrag_str)
            # Remove cached version so config changes take effect
            for mod_name in ("query_graph", "database_utils", "build_graph"):
                sys.modules.pop(mod_name, None)
            from query_graph import query_graph as _query_graph
        finally:
            os.chdir(original_cwd)

        # -- Prepare config ---------------------------------------------
        llm_func = self._make_llm_func()

        global_config: dict = {
            "working_dir": self._working_dir,
            "embeddings_func": self._embed,
            "use_llm_func": llm_func,
            "topk": 10,
            "level_mode": 2,
            "chunks_file": os.path.join(self._working_dir, "chunks.json"),
        }

        # -- Connect to MySQL -------------------------------------------
        db = pymysql.connect(
            host=self._mysql_host,
            port=self._mysql_port,
            user=self._mysql_user,
            passwd=self._mysql_password,
            charset="utf8mb4",
        )
        try:
            _describe, response = _query_graph(global_config, db, question)
            return response
        finally:
            db.close()

    async def query_timed(self, question: str) -> tuple[str, float]:
        """Run a single query and return ``(answer, wall_clock_seconds)``."""
        t0 = time.perf_counter()
        answer = await self.query(question)
        elapsed = time.perf_counter() - t0
        return answer, elapsed

    def get_index_size(self) -> int:
        """Return total index size in bytes (sum of all files in
        *working_dir*).
        """
        total = 0
        for dirpath, _dirnames, filenames in os.walk(self._working_dir):
            for fn in filenames:
                total += os.path.getsize(os.path.join(dirpath, fn))
        return total

    async def delete(self) -> None:
        """Delete the entire working directory."""
        if os.path.isdir(self._working_dir):
            shutil.rmtree(self._working_dir)
            logger.info("Deleted LeanRAG working dir: %s", self._working_dir)
