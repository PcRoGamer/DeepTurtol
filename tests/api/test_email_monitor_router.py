"""Tests for the email monitor API router."""

from __future__ import annotations

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

from deeptutor.api.routers import email_monitor as email_router
from deeptutor.services.email_monitor import EmailMonitorSettings


class FakeStore:
    """In-memory store for testing."""

    def __init__(self):
        self._settings = EmailMonitorSettings(enabled=True, consent_granted=True)
        self._summaries: dict[str, dict] = {}

    def get_settings(self):
        return self._settings

    def save_settings(self, settings):
        self._settings = settings

    def mask_password(self, settings):
        data = settings.model_dump()
        if data.get("password"):
            data["password"] = "********"
        return data

    def load_settings(self):
        return self._settings

    def list_summaries(self):
        return list(self._summaries.keys())

    def load_summary(self, summary_id: str):
        return self._summaries.get(summary_id)


class FakeService:
    """In-memory service for testing."""

    def __init__(self):
        self.status = {
            "enabled": True,
            "running": False,
            "poll_count": 0,
            "todos_created": 0,
        }

    async def poll_now(self):
        return {
            "success": True,
            "messages_fetched": 0,
            "todos_created": 0,
            "errors": [],
        }

    async def summarize(self, since_days: int = 1, mailbox: str | None = None):
        return {
            "success": True,
            "summary": {"title": "Test Digest"},
            "message_count": 0,
        }

    def get_status(self):
        return self.status


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(email_router, "get_email_monitor_store", lambda: FakeStore())
    monkeypatch.setattr(
        email_router, "get_email_monitor_service", lambda: FakeService()
    )

    app = FastAPI()
    app.include_router(email_router.router)
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


class TestEmailMonitorSettings:
    """Tests for /settings endpoints."""

    def test_get_settings(self, client):
        resp = client.get("/api/v1/email-monitor/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["settings"]["enabled"] is True

    def test_update_settings(self, client):
        resp = client.put(
            "/api/v1/email-monitor/settings", json={"enabled": False}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["settings"]["enabled"] is False

    def test_update_settings_partial(self, client):
        """Partial update should preserve unset fields."""
        resp = client.put(
            "/api/v1/email-monitor/settings",
            json={"imap_host": "imap.test.com", "imap_port": 993},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["settings"]["imap_host"] == "imap.test.com"
        assert data["settings"]["imap_port"] == 993
        # Original fields should remain
        assert data["settings"]["enabled"] is True


class TestEmailMonitorTestConnection:
    """Tests for /test endpoint."""

    def test_connection_test(self, client, monkeypatch):
        """Test endpoint returns connection result."""
        # Patch ImapConnector to avoid real IMAP calls
        class FakeConnector:
            def test_connection(self):
                from deeptutor.services.email_monitor import ConnectionResult

                return ConnectionResult(
                    success=True,
                    message="Connected successfully",
                    folder_info="INBOX (UIDVALIDITY 123, EXISTS 42)",
                )

        monkeypatch.setattr(email_router, "ImapConnector", lambda _: FakeConnector())

        resp = client.post("/api/v1/email-monitor/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Connected successfully"
        assert "UIDVALIDITY" in (data.get("folder_info") or "")


class TestEmailMonitorPoll:
    """Tests for /poll-now and /status endpoints."""

    def test_poll_now(self, client):
        resp = client.post("/api/v1/email-monitor/poll-now")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_get_status(self, client):
        resp = client.get("/api/v1/email-monitor/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["status"]["enabled"] is True


class TestEmailMonitorSummarize:
    """Tests for /summarize endpoint."""

    def test_summarize_default(self, client):
        resp = client.post("/api/v1/email-monitor/summarize")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_summarize_with_days(self, client):
        resp = client.post(
            "/api/v1/email-monitor/summarize", json={"since_days": 3}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestEmailMonitorSummaries:
    """Tests for /summaries and /summaries/{id} endpoints."""

    def test_list_summaries_empty(self, client):
        resp = client.get("/api/v1/email-monitor/summaries")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["summaries"] == []

    def test_list_summaries_with_data(self, monkeypatch):
        store = FakeStore()
        store._summaries["digest-2026-01-01"] = {"title": "Test Digest"}
        monkeypatch.setattr(email_router, "get_email_monitor_store", lambda: store)
        monkeypatch.setattr(
            email_router, "get_email_monitor_service", lambda: FakeService()
        )

        app = FastAPI()
        app.include_router(email_router.router)
        with TestClient(app) as c:
            resp = c.get("/api/v1/email-monitor/summaries")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["summaries"]) == 1
        assert data["summaries"][0]["id"] == "digest-2026-01-01"

    def test_get_summary_found(self, monkeypatch):
        store = FakeStore()
        store._summaries["digest-2026-01-01"] = {"title": "Test Digest"}
        monkeypatch.setattr(email_router, "get_email_monitor_store", lambda: store)
        monkeypatch.setattr(
            email_router, "get_email_monitor_service", lambda: FakeService()
        )

        app = FastAPI()
        app.include_router(email_router.router)
        with TestClient(app) as c:
            resp = c.get(
                "/api/v1/email-monitor/summaries/digest-2026-01-01"
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["summary"]["title"] == "Test Digest"

    def test_get_summary_not_found(self, client):
        resp = client.get(
            "/api/v1/email-monitor/summaries/nonexistent-id"
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "not found" in data["detail"].lower()
