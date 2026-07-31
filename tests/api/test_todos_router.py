"""Tests for the Todos API router."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - optional dependency in lightweight envs
    FastAPI = None
    TestClient = None

pytestmark = pytest.mark.skipif(
    FastAPI is None or TestClient is None, reason="fastapi not installed"
)

if FastAPI is not None and TestClient is not None:
    from deeptutor.api.routers import todos as todos_router
    from deeptutor.services.todos import TodoItem
else:  # pragma: no cover - optional dependency in lightweight envs
    todos_router = None
    TodoItem = None


def _build_app() -> FastAPI:
    if FastAPI is None or todos_router is None:  # pragma: no cover
        raise RuntimeError("fastapi is not installed")
    app = FastAPI()
    app.include_router(todos_router.router)
    return app


class _FakeTodoService:
    """In-memory fake for TodoService used in router tests."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"fake-{self._counter}"

    @staticmethod
    def _ts() -> float:
        return 1000.0

    def _to_item(self, raw: dict) -> TodoItem:
        return TodoItem.model_validate(raw)

    def create_item(self, data: dict) -> TodoItem:
        now = self._ts()
        item: dict = {
            "id": self._next_id(),
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
            "created_at": now,
            "updated_at": now,
            "completed_at": data.get("completed_at"),
        }
        self.items[item["id"]] = item
        return self._to_item(item)

    def list_items(self, **kwargs) -> list[TodoItem]:
        items = list(self.items.values())
        status = kwargs.get("status")
        kind = kwargs.get("kind")
        due_before = kwargs.get("due_before")
        due_after = kwargs.get("due_after")

        result = []
        for item in items:
            if status is not None and item.get("status") != status:
                continue
            if kind is not None and item.get("kind") != kind:
                continue
            due = item.get("due_at")
            if due_before is not None and (due is None or due > due_before):
                continue
            if due_after is not None and (due is None or due < due_after):
                continue
            result.append(item)
        return [self._to_item(it) for it in result]

    def get_upcoming_items(self) -> list[TodoItem]:
        open_items = [it for it in self.items.values() if it.get("status") == "open"]
        open_items.sort(
            key=lambda it: (
                0 if it.get("due_at") else 1,
                it.get("due_at") or datetime.max,
            )
        )
        return [self._to_item(it) for it in open_items]

    def update_item(self, item_id: str, updates: dict) -> TodoItem:
        if item_id not in self.items:
            raise KeyError(f"TodoItem with id {item_id!r} not found")
        item = self.items[item_id]
        for key, value in updates.items():
            if key in ("id", "created_at"):
                continue
            item[key] = value
        item["updated_at"] = self._ts()
        return self._to_item(item)

    def delete_item(self, item_id: str) -> bool:
        if item_id not in self.items:
            return False
        del self.items[item_id]
        return True


# ── fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def fake_service(monkeypatch: pytest.MonkeyPatch) -> _FakeTodoService:
    service = _FakeTodoService()
    monkeypatch.setattr(todos_router, "get_todo_service", lambda: service)
    return service


# ── GET /api/v1/todos ──────────────────────────────────────────────


class TestListTodos:
    def test_empty(self, fake_service: _FakeTodoService) -> None:
        with TestClient(_build_app()) as client:
            resp = client.get("/api/v1/todos")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["todos"] == []

    def test_with_items(self, fake_service: _FakeTodoService) -> None:
        fake_service.create_item({"title": "Alpha"})
        fake_service.create_item({"title": "Beta"})

        with TestClient(_build_app()) as client:
            resp = client.get("/api/v1/todos")
        assert resp.status_code == 200
        assert len(resp.json()["todos"]) == 2

    def test_filter_by_status(self, fake_service: _FakeTodoService) -> None:
        fake_service.create_item({"title": "Open item"})
        done = fake_service.create_item({"title": "Done item"})
        fake_service.update_item(done.id, {"status": "done"})

        with TestClient(_build_app()) as client:
            open_resp = client.get("/api/v1/todos", params={"status": "open"})
            done_resp = client.get("/api/v1/todos", params={"status": "done"})

        assert len(open_resp.json()["todos"]) == 1
        assert open_resp.json()["todos"][0]["title"] == "Open item"
        assert len(done_resp.json()["todos"]) == 1
        assert done_resp.json()["todos"][0]["title"] == "Done item"

    def test_filter_by_kind(self, fake_service: _FakeTodoService) -> None:
        fake_service.create_item({"title": "Assignment", "kind": "assignment"})
        fake_service.create_item({"title": "Meeting", "kind": "meeting"})

        with TestClient(_build_app()) as client:
            resp = client.get("/api/v1/todos", params={"kind": "assignment"})
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()["todos"]]
        assert titles == ["Assignment"]

    def test_filter_by_due_before(self, fake_service: _FakeTodoService) -> None:
        early = datetime(2024, 1, 1, tzinfo=timezone.utc)
        late = datetime(2024, 6, 1, tzinfo=timezone.utc)
        fake_service.create_item({"title": "Early", "due_at": early})
        fake_service.create_item({"title": "Late", "due_at": late})

        with TestClient(_build_app()) as client:
            resp = client.get(
                "/api/v1/todos",
                params={"due_before": "2024-03-01T00:00:00Z"},
            )
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()["todos"]]
        assert titles == ["Early"]

    def test_filter_by_due_after(self, fake_service: _FakeTodoService) -> None:
        early = datetime(2024, 1, 1, tzinfo=timezone.utc)
        late = datetime(2024, 6, 1, tzinfo=timezone.utc)
        fake_service.create_item({"title": "Early", "due_at": early})
        fake_service.create_item({"title": "Late", "due_at": late})

        with TestClient(_build_app()) as client:
            resp = client.get(
                "/api/v1/todos",
                params={"due_after": "2024-03-01T00:00:00Z"},
            )
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()["todos"]]
        assert titles == ["Late"]


# ── POST /api/v1/todos ─────────────────────────────────────────────


class TestCreateTodo:
    def test_create(self, fake_service: _FakeTodoService) -> None:
        with TestClient(_build_app()) as client:
            resp = client.post("/api/v1/todos", json={"title": "My todo"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["todo"]["title"] == "My todo"
        assert data["todo"]["source"] == "manual"
        assert data["todo"]["status"] == "open"

    def test_create_with_all_fields(self, fake_service: _FakeTodoService) -> None:
        payload = {
            "title": "Full todo",
            "due_at": "2024-12-25T00:00:00Z",
            "kind": "assignment",
            "course": "MATH 101",
            "priority": "high",
            "notes": "Important",
        }
        with TestClient(_build_app()) as client:
            resp = client.post("/api/v1/todos", json=payload)
        assert resp.status_code == 200
        todo = resp.json()["todo"]
        assert todo["title"] == "Full todo"
        assert todo["kind"] == "assignment"
        assert todo["course"] == "MATH 101"
        assert todo["priority"] == "high"
        assert todo["notes"] == "Important"

    def test_validates_empty_title(self, fake_service: _FakeTodoService) -> None:
        with TestClient(_build_app()) as client:
            resp = client.post("/api/v1/todos", json={"title": ""})
        assert resp.status_code == 422

    def test_validates_missing_title(self, fake_service: _FakeTodoService) -> None:
        with TestClient(_build_app()) as client:
            resp = client.post("/api/v1/todos", json={})
        assert resp.status_code == 422


# ── GET /api/v1/todos/upcoming ─────────────────────────────────────


class TestGetUpcoming:
    def test_returns_open_items_sorted(self, fake_service: _FakeTodoService) -> None:
        later = datetime(2024, 6, 1, tzinfo=timezone.utc)
        earlier = datetime(2024, 1, 1, tzinfo=timezone.utc)
        fake_service.create_item({"title": "Later", "due_at": later})
        fake_service.create_item({"title": "Earlier", "due_at": earlier})
        fake_service.create_item({"title": "No due"})

        with TestClient(_build_app()) as client:
            resp = client.get("/api/v1/todos/upcoming")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        titles = [t["title"] for t in data["todos"]]
        assert titles == ["Earlier", "Later", "No due"]

    def test_excludes_done_and_dismissed(self, fake_service: _FakeTodoService) -> None:
        fake_service.create_item({"title": "Open"})
        done = fake_service.create_item({"title": "Done"})
        dismissed = fake_service.create_item({"title": "Dismissed"})
        fake_service.update_item(done.id, {"status": "done"})
        fake_service.update_item(dismissed.id, {"status": "dismissed"})

        with TestClient(_build_app()) as client:
            resp = client.get("/api/v1/todos/upcoming")
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()["todos"]]
        assert titles == ["Open"]

    def test_empty_when_no_open(self, fake_service: _FakeTodoService) -> None:
        with TestClient(_build_app()) as client:
            resp = client.get("/api/v1/todos/upcoming")
        assert resp.status_code == 200
        assert resp.json()["todos"] == []


# ── PATCH /api/v1/todos/{todo_id} ──────────────────────────────────


class TestUpdateTodo:
    def test_update_title(self, fake_service: _FakeTodoService) -> None:
        item = fake_service.create_item({"title": "Original"})

        with TestClient(_build_app()) as client:
            resp = client.patch(
                f"/api/v1/todos/{item.id}",
                json={"title": "Updated"},
            )
        assert resp.status_code == 200
        assert resp.json()["todo"]["title"] == "Updated"

    def test_update_status_to_done(self, fake_service: _FakeTodoService) -> None:
        item = fake_service.create_item({"title": "Task"})

        with TestClient(_build_app()) as client:
            resp = client.patch(
                f"/api/v1/todos/{item.id}",
                json={"status": "done"},
            )
        assert resp.status_code == 200
        assert resp.json()["todo"]["status"] == "done"

    def test_update_status_to_dismissed(self, fake_service: _FakeTodoService) -> None:
        item = fake_service.create_item({"title": "Task"})

        with TestClient(_build_app()) as client:
            resp = client.patch(
                f"/api/v1/todos/{item.id}",
                json={"status": "dismissed"},
            )
        assert resp.status_code == 200
        assert resp.json()["todo"]["status"] == "dismissed"

    def test_partial_update_only_changes_sent_fields(
        self, fake_service: _FakeTodoService
    ) -> None:
        item = fake_service.create_item(
            {"title": "Task", "priority": "high", "notes": "Original notes"}
        )

        with TestClient(_build_app()) as client:
            resp = client.patch(
                f"/api/v1/todos/{item.id}",
                json={"priority": "low"},
            )
        assert resp.status_code == 200
        todo = resp.json()["todo"]
        assert todo["priority"] == "low"
        assert todo["notes"] == "Original notes"  # unchanged
        assert todo["title"] == "Task"  # unchanged

    def test_returns_404_for_unknown_id(self, fake_service: _FakeTodoService) -> None:
        with TestClient(_build_app()) as client:
            resp = client.patch(
                "/api/v1/todos/nonexistent",
                json={"title": "Nope"},
            )
        assert resp.status_code == 404
        assert "nonexistent" in resp.json()["detail"]


# ── DELETE /api/v1/todos/{todo_id} ─────────────────────────────────


class TestDeleteTodo:
    def test_delete_existing(self, fake_service: _FakeTodoService) -> None:
        item = fake_service.create_item({"title": "Delete me"})

        with TestClient(_build_app()) as client:
            resp = client.delete(f"/api/v1/todos/{item.id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["message"] == f"Todo {item.id} deleted"

        # Verify it's gone
        with TestClient(_build_app()) as client:
            listing = client.get("/api/v1/todos")
        assert len(listing.json()["todos"]) == 0

    def test_returns_404_for_unknown_id(self, fake_service: _FakeTodoService) -> None:
        with TestClient(_build_app()) as client:
            resp = client.delete("/api/v1/todos/nonexistent")
        assert resp.status_code == 404
        assert "nonexistent" in resp.json()["detail"]
