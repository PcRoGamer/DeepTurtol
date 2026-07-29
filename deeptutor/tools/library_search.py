"""Read-only search over the user's durable lecture and video library."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from deeptutor.services.path_service import get_path_service

_ITEM_ID = re.compile(r"^[a-f0-9]{32}$")
_TEXT_LIMIT = 18_000


@dataclass(frozen=True)
class LibrarySearchResult:
    text: str
    sources: list[dict]
    metadata: dict


def _root() -> Path:
    return get_path_service().get_user_root() / "media_library"


def _items() -> list[tuple[Path, dict]]:
    root = _root()
    if not root.is_dir():
        return []
    items: list[tuple[Path, dict]] = []
    for item_dir in root.iterdir():
        metadata_path = item_dir / "metadata.json"
        if not item_dir.is_dir() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(metadata, dict):
            items.append((item_dir, metadata))
    items.sort(key=lambda entry: str(entry[1].get("created_at") or ""), reverse=True)
    return items


def _artifact(item_dir: Path, metadata: dict, name: str) -> str:
    filename = metadata.get(f"{name}_file")
    if not filename:
        return ""
    path = item_dir / str(filename)
    try:
        path.resolve().relative_to(item_dir.resolve())
    except ValueError:
        return ""
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError:
        return ""


def _source(metadata: dict, content: str = "") -> dict:
    return {
        "type": "media_library",
        "id": str(metadata.get("id") or ""),
        "title": str(metadata.get("title") or "Untitled lecture"),
        "source": str(metadata.get("source") or "recording"),
        "course_name": str(metadata.get("course_name") or ""),
        "content": content[:2_000],
    }


def query_library(
    *,
    action: str = "search",
    query: str = "",
    item_id: str = "",
    artifact: str = "notes",
    limit: int = 8,
) -> LibrarySearchResult:
    """List, search, or read library transcripts and generated study notes."""
    entries = _items()
    limit = max(1, min(int(limit or 8), 20))
    if action == "list":
        selected = entries[:limit]
        lines = [
            (
                f"- `{meta.get('id', '')}` — {meta.get('title', 'Untitled lecture')} "
                f"[{meta.get('status', 'unknown')}]"
                + (f" — {meta.get('course_name')}" if meta.get("course_name") else "")
            )
            for _, meta in selected
        ]
        return LibrarySearchResult(
            text="\n".join(lines) or "The media library is empty.",
            sources=[_source(meta) for _, meta in selected],
            metadata={"count": len(selected), "action": action},
        )

    if action == "read":
        if not _ITEM_ID.match(item_id):
            return LibrarySearchResult(
                text="A valid library item_id is required.",
                sources=[],
                metadata={"action": action, "error": "invalid_item_id"},
            )
        match = next(
            ((item_dir, meta) for item_dir, meta in entries if meta.get("id") == item_id),
            None,
        )
        if match is None:
            return LibrarySearchResult(
                text="Library item not found.",
                sources=[],
                metadata={"action": action, "error": "not_found"},
            )
        item_dir, metadata = match
        chosen = artifact if artifact in {"notes", "transcript"} else "notes"
        content = _artifact(item_dir, metadata, chosen)
        if not content and chosen == "notes":
            content = _artifact(item_dir, metadata, "transcript")
        return LibrarySearchResult(
            text=(content[:_TEXT_LIMIT] or str(metadata.get("progress") or "No text is ready.")),
            sources=[_source(metadata, content)],
            metadata={"action": action, "item_id": item_id, "artifact": chosen},
        )

    terms = [term for term in re.findall(r"[\w'-]+", query.casefold()) if len(term) > 1]
    if not terms:
        return LibrarySearchResult(
            text="Provide a topic or phrase to search the media library.",
            sources=[],
            metadata={"action": "search", "error": "empty_query"},
        )
    ranked: list[tuple[int, dict, str]] = []
    for item_dir, metadata in entries:
        notes = _artifact(item_dir, metadata, "notes")
        transcript = _artifact(item_dir, metadata, "transcript")
        haystack = " ".join(
            [
                str(metadata.get("title") or ""),
                str(metadata.get("summary") or ""),
                str(metadata.get("course_name") or ""),
                notes,
                transcript,
            ]
        ).casefold()
        score = sum(haystack.count(term) for term in terms)
        if score:
            content = notes or transcript or str(metadata.get("summary") or "")
            ranked.append((score, metadata, content))
    ranked.sort(
        key=lambda row: (row[0], str(row[1].get("created_at") or "")),
        reverse=True,
    )
    selected = ranked[:limit]
    lines = [
        (
            f"## {metadata.get('title', 'Untitled lecture')}\n"
            f"Library ID: `{metadata.get('id', '')}`\n"
            f"{content[:2_500]}"
        )
        for _, metadata, content in selected
    ]
    return LibrarySearchResult(
        text="\n\n".join(lines) or "No library recordings matched that search.",
        sources=[_source(metadata, content) for _, metadata, content in selected],
        metadata={"action": "search", "count": len(selected), "query": query},
    )


__all__ = ["LibrarySearchResult", "query_library"]
