"""Shared protocol both RAG adapters implement."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RAGBenchmark(Protocol):
    """Contract for a RAG system under benchmark."""

    async def initialize(self, working_dir: str) -> None:
        """One-time setup (connect to DBs, etc.)."""
        ...

    async def index(self, doc_paths: list[str], label: str = "") -> float:
        """Build a fresh index from doc_paths. Returns wall-clock seconds."""
        ...

    async def add_documents(self, doc_paths: list[str], label: str = "") -> float:
        """Incrementally add documents. Returns wall-clock seconds."""
        ...

    async def query(self, question: str) -> str:
        """Run a single query, return the answer string."""
        ...

    async def query_timed(self, question: str) -> tuple[str, float]:
        """Run a single query, return (answer, wall-clock seconds)."""
        ...

    def get_index_size(self) -> int:
        """Return total index size in bytes."""
        ...

    async def delete(self) -> None:
        """Delete the entire index and clean up."""
        ...
