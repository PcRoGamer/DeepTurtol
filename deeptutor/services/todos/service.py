"""TodoService — JSON CRUD for personal todo items.

Stored under ``data/user/workspace/todos/todos.json``.
Mirrors the ``NotebookManager`` pattern from ``deeptutor/services/notebook/service.py``.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from .models import TodoItem

# ── helpers ──────────────────────────────────────────────────────────


def _default_serializer(o: object) -> str:
    """``json.dumps`` default — delegates datetimes to ISO format."""
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def _parse_datetime(value: object) -> datetime | None:
    """Rebuild a ``datetime`` from an ISO string or pass through an existing datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None


def _migrate_item(raw: dict) -> dict:
    """Normalise a raw dict so it round-trips through ``TodoItem.model_validate``."""
    for field in ("due_at", "source_received_at"):
        val = raw.get(field)
        if isinstance(val, str):
            raw[field] = _parse_datetime(val)
    return raw


# ── service ──────────────────────────────────────────────────────────


class TodoService:
    """Manage todo items in a single JSON file.

    Thread-safe for single-process use; no locking is performed.
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.todo_file = self.base_dir / "todos.json"

    # ── JSON I/O ───────────────────────────────────────────────────

    def _load_items(self) -> list[dict]:
        if not self.todo_file.exists():
            return []
        try:
            with open(self.todo_file, encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("items", [])
            return [_migrate_item(it) for it in items]
        except Exception:
            return []

    def _save_items(self, items: list[dict]) -> None:
        tmp = self.todo_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"items": items},
                f,
                indent=2,
                ensure_ascii=False,
                default=_default_serializer,
            )
        os.replace(str(tmp), str(self.todo_file))

    # ── CRUD ───────────────────────────────────────────────────────

    def create_item(self, data: dict) -> TodoItem:
        item: dict = {
            "id": str(uuid.uuid4())[:8],
            "title": data.get("title", ""),
            "status": data.get("status", "open"),
            "due_at": data.get("due_at"),
            "due_at_confidence": data.get("due_at_confidence"),
            "kind": data.get("kind", "manual"),
            "course": data.get("course"),
            "priority": data.get("priority", "normal"),
            "notes": data.get("notes", ""),
            "source": data.get("source", "manual"),
            "source_message_id": data.get("source_message_id"),
            "source_subject": data.get("source_subject"),
            "source_from": data.get("source_from"),
            "source_received_at": data.get("source_received_at"),
            "created_at": time.time(),
            "updated_at": time.time(),
            "completed_at": data.get("completed_at"),
        }
        # If status is "done" but no completed_at, set it now.
        if item["status"] == "done" and item["completed_at"] is None:
            item["completed_at"] = time.time()

        items = self._load_items()
        items.append(item)
        self._save_items(items)
        return TodoItem.model_validate(item)

    def list_items(
        self,
        status: str | None = None,
        kind: str | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
    ) -> list[TodoItem]:
        items = self._load_items()
        result: list[dict] = []

        for item in items:
            if status is not None and item.get("status") != status:
                continue
            if kind is not None and item.get("kind") != kind:
                continue
            due = _parse_datetime(item.get("due_at"))
            if due_before is not None and (due is None or due > due_before):
                continue
            if due_after is not None and (due is None or due < due_after):
                continue
            result.append(item)

        return [TodoItem.model_validate(it) for it in result]

    def get_item(self, item_id: str) -> TodoItem | None:
        items = self._load_items()
        for item in items:
            if item.get("id") == item_id:
                return TodoItem.model_validate(item)
        return None

    def update_item(self, item_id: str, updates: dict) -> TodoItem:
        items = self._load_items()
        for item in items:
            if item.get("id") != item_id:
                continue

            for key, value in updates.items():
                if key in ("id", "created_at"):
                    continue  # immutable fields
                # If setting status to done, auto-set completed_at
                if key == "status" and value == "done":
                    if not item.get("completed_at"):
                        item["completed_at"] = time.time()
                # If status is changed away from done, clear completed_at
                if key == "status" and value != "done" and item.get("status") == "done":
                    item["completed_at"] = None
                item[key] = value

            item["updated_at"] = time.time()
            self._save_items(items)
            return TodoItem.model_validate(item)

        raise KeyError(f"TodoItem with id {item_id!r} not found")

    def delete_item(self, item_id: str) -> bool:
        items = self._load_items()
        before = len(items)
        items = [it for it in items if it.get("id") != item_id]
        if len(items) == before:
            return False
        self._save_items(items)
        return True

    def get_upcoming_items(self) -> list[TodoItem]:
        items = self._load_items()
        open_items = [it for it in items if it.get("status") == "open"]
        open_items.sort(
            key=lambda it: (
                0 if it.get("due_at") else 1,
                _parse_datetime(it.get("due_at")) or datetime.max,
            )
        )
        return [TodoItem.model_validate(it) for it in open_items]

    # ── dedup ──────────────────────────────────────────────────────

    def find_by_source(
        self,
        source_message_id: str,
        normalized_title: str,
    ) -> list[TodoItem]:
        """Return items matching the same email message id *and* title.

        Used as a secondary guard against double-insertion when the
        ledger may have been wiped but the email monitor re-processes the
        same message.
        """
        items = self._load_items()
        matches: list[dict] = []
        for item in items:
            if item.get("source_message_id") == source_message_id and item.get(
                "title"
            ) == normalized_title:
                matches.append(item)
        return [TodoItem.model_validate(it) for it in matches]


# ── singleton factory ──────────────────────────────────────────────


_instances: dict[str, TodoService] = {}


def get_todo_service(base_dir: str | None = None) -> TodoService:
    if base_dir is None:
        from deeptutor.services.path_service import get_path_service

        base_dir = str(get_path_service().get_workspace_feature_dir("todos"))
    key = str(Path(base_dir).resolve())
    if key not in _instances:
        _instances[key] = TodoService(base_dir=base_dir)
    return _instances[key]


class _TodoServiceProxy:
    """Convenience proxy so callers can write ``todo_service.create_item(...)``."""

    def __getattr__(self, name: str):
        return getattr(get_todo_service(), name)


todo_service: TodoService = _TodoServiceProxy()  # type: ignore[assignment]
