from __future__ import annotations

import json
from pathlib import Path

from deeptutor.agents._shared.tool_composition import (
    ToolMountFlags,
    compose_enabled_tools,
    default_optional_tools,
)
from deeptutor.runtime.registry.tool_registry import ToolRegistry
from deeptutor.tools import library_search


def test_search_and_read_library_notes(tmp_path: Path, monkeypatch):
    item_id = "a" * 32
    item = tmp_path / item_id
    item.mkdir()
    (item / "metadata.json").write_text(
        json.dumps(
            {
                "id": item_id,
                "title": "Graph traversal",
                "status": "ready",
                "source": "echo360",
                "course_name": "Algorithms",
                "notes_file": "notes.md",
                "transcript_file": "transcript.txt",
                "created_at": "2026-07-20T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (item / "notes.md").write_text(
        "Breadth-first search explores a graph level by level.",
        encoding="utf-8",
    )
    (item / "transcript.txt").write_text("Full graph lecture.", encoding="utf-8")
    monkeypatch.setattr(library_search, "_root", lambda: tmp_path)

    result = library_search.query_library(action="search", query="breadth-first graph")
    read = library_search.query_library(
        action="read",
        item_id=item_id,
        artifact="transcript",
    )

    assert "Graph traversal" in result.text
    assert result.sources[0]["source"] == "echo360"
    assert read.text == "Full graph lecture."


def test_library_search_is_always_available_to_chat_agent():
    registry = ToolRegistry()
    registry.load_builtins()

    enabled = compose_enabled_tools(
        registry=registry,
        requested_tools=[],
        optional_whitelist=default_optional_tools(),
        mount_flags=ToolMountFlags(),
    )

    assert "library_search" in enabled
