"""TodoItem Pydantic model for the personal todos system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TodoItem(BaseModel):
    """A single todo item stored in ``data/user/workspace/todos/todos.json``."""

    id: str
    title: str
    status: Literal["open", "done", "dismissed"] = "open"
    due_at: datetime | None = None
    due_at_confidence: Literal["high", "medium", "low"] | None = None
    kind: Literal["assignment", "exam", "meeting", "admin", "other", "manual"] = "manual"
    course: str | None = None
    priority: Literal["low", "normal", "high"] = "normal"
    notes: str = ""
    source: Literal["email", "manual"] = "manual"
    source_message_id: str | None = None
    source_subject: str | None = None
    source_from: str | None = None
    source_received_at: datetime | None = None
    created_at: float
    updated_at: float
    completed_at: float | None = None
