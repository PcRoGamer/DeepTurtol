"""Storage helpers for LazyGraphRAG's vector-backed index."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from deeptutor.services.rag.embedding_signature import embedding_meta_fields
from deeptutor.services.rag.index_versioning import list_kb_versions

PROVIDER = "lazygraphrag"


def write_meta(root_dir: Path) -> None:
    """Record ownership without coupling the index to an embedding version."""
    root_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": root_dir.name,
        "signature": PROVIDER,
        "provider": PROVIDER,
        "layout": "flat",
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        **embedding_meta_fields(),
    }
    with open(root_dir / "meta.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def find_storage(kb_dir: Path) -> Path | None:
    """Return the newest ready storage directory owned by this provider."""
    for entry in list_kb_versions(kb_dir):
        if entry.get("provider") == PROVIDER or entry.get("signature") == PROVIDER:
            path = Path(str(entry.get("storage_path") or ""))
            if path.is_dir() and (path / "docstore.json").exists():
                return path
    return None


__all__ = ["PROVIDER", "find_storage", "write_meta"]
