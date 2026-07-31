"""Comprehensive CRUD tests for TodoService."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from deeptutor.services.todos.models import TodoItem
from deeptutor.services.todos.service import TodoService


def _make_service(tmp_path: Path) -> TodoService:
    return TodoService(base_dir=str(tmp_path))


# ── create ──────────────────────────────────────────────────────────


def test_create_item_returns_valid_todo(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    todo = svc.create_item({"title": "Finish homework"})

    assert isinstance(todo, TodoItem)
    assert todo.id is not None and len(todo.id) == 8
    assert todo.title == "Finish homework"
    assert todo.status == "open"
    assert todo.kind == "manual"
    assert todo.priority == "normal"
    assert todo.source == "manual"
    assert todo.notes == ""
    assert todo.created_at > 0
    assert todo.updated_at >= todo.created_at
    assert todo.completed_at is None


def test_create_item_with_all_fields(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    due = datetime(2026, 9, 15, 23, 59)
    todo = svc.create_item(
        {
            "title": "Submit lab report",
            "status": "open",
            "due_at": due,
            "due_at_confidence": "high",
            "kind": "assignment",
            "course": "PHYS101",
            "priority": "high",
            "notes": "Needs graphs",
            "source": "email",
            "source_message_id": "msg_001",
            "source_subject": "Lab report reminder",
            "source_from": "prof@univ.edu",
            "source_received_at": due - timedelta(days=1),
        }
    )

    assert todo.title == "Submit lab report"
    assert todo.status == "open"
    assert todo.due_at == due
    assert todo.due_at_confidence == "high"
    assert todo.kind == "assignment"
    assert todo.course == "PHYS101"
    assert todo.priority == "high"
    assert todo.notes == "Needs graphs"
    assert todo.source == "email"
    assert todo.source_message_id == "msg_001"
    assert todo.source_subject == "Lab report reminder"
    assert todo.source_from == "prof@univ.edu"
    assert todo.source_received_at is not None


def test_create_done_item_sets_completed_at(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    todo = svc.create_item({"title": "Done task", "status": "done"})
    assert todo.status == "done"
    assert todo.completed_at is not None


# ── list ────────────────────────────────────────────────────────────


def test_list_items_all(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    svc.create_item({"title": "A"})
    svc.create_item({"title": "B"})
    items = svc.list_items()
    assert len(items) == 2


def test_list_items_filter_by_status(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    svc.create_item({"title": "Open task"})
    svc.create_item({"title": "Done task", "status": "done"})

    open_items = svc.list_items(status="open")
    assert len(open_items) == 1
    assert open_items[0].title == "Open task"

    done_items = svc.list_items(status="done")
    assert len(done_items) == 1
    assert done_items[0].title == "Done task"


def test_list_items_filter_by_kind(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    svc.create_item({"title": "Exam", "kind": "exam"})
    svc.create_item({"title": "Admin", "kind": "admin"})

    exams = svc.list_items(kind="exam")
    assert len(exams) == 1
    assert exams[0].title == "Exam"


def test_list_items_filter_by_due_before(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    early = datetime(2026, 1, 1)
    late = datetime(2026, 6, 1)
    svc.create_item({"title": "Early", "due_at": early})
    svc.create_item({"title": "Late", "due_at": late})
    svc.create_item({"title": "No due"})

    before_march = svc.list_items(due_before=datetime(2026, 3, 1))
    assert len(before_march) == 1
    assert before_march[0].title == "Early"


def test_list_items_filter_by_due_after(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    early = datetime(2026, 1, 1)
    late = datetime(2026, 6, 1)
    svc.create_item({"title": "Early", "due_at": early})
    svc.create_item({"title": "Late", "due_at": late})

    after_march = svc.list_items(due_after=datetime(2026, 3, 1))
    assert len(after_march) == 1
    assert after_march[0].title == "Late"


def test_list_items_combined_filters(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    due = datetime(2026, 6, 1)
    svc.create_item({"title": "Match", "status": "open", "kind": "assignment", "due_at": due})
    svc.create_item({"title": "Wrong status", "status": "done", "kind": "assignment", "due_at": due})
    svc.create_item({"title": "Wrong kind", "status": "open", "kind": "exam", "due_at": due})

    result = svc.list_items(status="open", kind="assignment", due_before=datetime(2026, 7, 1))
    assert len(result) == 1
    assert result[0].title == "Match"


# ── get ─────────────────────────────────────────────────────────────


def test_get_item_found(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    created = svc.create_item({"title": "Find me"})
    fetched = svc.get_item(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Find me"


def test_get_item_not_found(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    assert svc.get_item("nonexistent") is None


# ── update ──────────────────────────────────────────────────────────


def test_update_item_title(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    todo = svc.create_item({"title": "Old title"})
    updated = svc.update_item(todo.id, {"title": "New title"})
    assert updated.title == "New title"
    assert updated.updated_at > todo.updated_at

    # Verify persisted
    fetched = svc.get_item(todo.id)
    assert fetched is not None
    assert fetched.title == "New title"


def test_update_item_status_to_done_sets_completed_at(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    todo = svc.create_item({"title": "Do it"})
    assert todo.completed_at is None

    updated = svc.update_item(todo.id, {"status": "done"})
    assert updated.status == "done"
    assert updated.completed_at is not None


def test_update_item_status_away_from_done_clears_completed_at(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    todo = svc.create_item({"title": "Reopen", "status": "done"})
    assert todo.completed_at is not None

    updated = svc.update_item(todo.id, {"status": "open"})
    assert updated.status == "open"
    assert updated.completed_at is None


def test_update_item_immutable_id_ignored(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    todo = svc.create_item({"title": "Original"})
    updated = svc.update_item(todo.id, {"id": "newid"})
    assert updated.id == todo.id  # unchanged


def test_update_item_not_found(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.update_item("doesnotexist", {"title": "Nope"})
        assert False, "Expected KeyError"
    except KeyError:
        pass


# ── delete ──────────────────────────────────────────────────────────


def test_delete_item_exists(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    todo = svc.create_item({"title": "Delete me"})
    assert svc.delete_item(todo.id) is True
    assert svc.get_item(todo.id) is None


def test_delete_item_not_found(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    assert svc.delete_item("nonexistent") is False


def test_delete_item_persists_remaining(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    a = svc.create_item({"title": "A"})
    svc.create_item({"title": "B"})
    svc.delete_item(a.id)
    remaining = svc.list_items()
    assert len(remaining) == 1
    assert remaining[0].title == "B"


# ── upcoming ────────────────────────────────────────────────────────


def test_get_upcoming_items_ordered_by_due(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    later = datetime(2026, 6, 1)
    earlier = datetime(2026, 1, 1)

    svc.create_item({"title": "Later", "due_at": later, "status": "open"})
    svc.create_item({"title": "Earlier", "due_at": earlier, "status": "open"})
    svc.create_item({"title": "No due", "status": "open"})
    svc.create_item({"title": "Done task", "due_at": earlier, "status": "done"})

    upcoming = svc.get_upcoming_items()
    # Only open items, sorted by due_at asc (null last)
    titles = [it.title for it in upcoming]
    assert "Done task" not in titles
    assert titles == ["Earlier", "Later", "No due"]


# ── find_by_source ──────────────────────────────────────────────────


def test_find_by_source_matches_message_id_and_title(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    svc.create_item(
        {
            "title": "Match",
            "source": "email",
            "source_message_id": "msg_42",
        }
    )
    svc.create_item(
        {
            "title": "Other",
            "source": "email",
            "source_message_id": "msg_42",
        }
    )
    svc.create_item(
        {
            "title": "Match",
            "source": "email",
            "source_message_id": "msg_99",
        }
    )

    found = svc.find_by_source("msg_42", "Match")
    assert len(found) == 1
    assert found[0].title == "Match"


def test_find_by_source_no_match(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    assert svc.find_by_source("nonexistent", "Anything") == []


# ── persistence ─────────────────────────────────────────────────────


def test_items_survive_service_recreation(tmp_path: Path) -> None:
    svc1 = _make_service(tmp_path)
    todo = svc1.create_item({"title": "Persist me"})

    svc2 = _make_service(tmp_path)
    loaded = svc2.get_item(todo.id)
    assert loaded is not None
    assert loaded.title == "Persist me"


def test_empty_list_when_file_missing(tmp_path: Path) -> None:
    svc = _make_service(tmp_path / "nonexistent")
    assert svc.list_items() == []


def test_todo_file_is_json(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    svc.create_item({"title": "Check file"})
    assert svc.todo_file.exists()
    content = svc.todo_file.read_text(encoding="utf-8")
    assert '"items"' in content
