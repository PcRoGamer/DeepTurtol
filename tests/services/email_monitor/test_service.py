"""Tests for EmailMonitorService — poll loop, extraction, todo creation, lifecycle.

All tests use ``FakeConnector`` (no real IMAP) and monkeypatch the
extractor to return controlled JSON (no real LLM calls).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from deeptutor.services.email_monitor.connectors.fake import FakeConnector
from deeptutor.services.email_monitor.models import (
    EmailMonitorSettings,
    RawMessage,
)
from deeptutor.services.email_monitor.service import EmailMonitorService
from deeptutor.services.email_monitor.store import EmailMonitorStore
from deeptutor.services.todos.service import TodoService


@pytest.fixture
def store(tmp_path: Path) -> EmailMonitorStore:
    """Create an EmailMonitorStore backed by tmp_path."""
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    return EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))


@pytest.fixture
def enabled_settings() -> EmailMonitorSettings:
    return EmailMonitorSettings(
        enabled=True,
        consent_granted=True,
        imap_host="fake",
        username="test@uni.edu",
        password="secret",
        poll_interval_seconds=600,
    )


@pytest.fixture
def fake_connector() -> FakeConnector:
    return FakeConnector()


@pytest.fixture
def service(store: EmailMonitorStore) -> EmailMonitorService:
    return EmailMonitorService(store=store)


@pytest.fixture
def todo_service(tmp_path: Path) -> TodoService:
    """Create an isolated TodoService backed by tmp_path."""
    return TodoService(base_dir=str(tmp_path / "todos"))


# ── Lifecycle tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_does_nothing_when_disabled(service: EmailMonitorService) -> None:
    """start() should be a no-op when the monitor is not enabled."""
    await service.start()
    assert service._running is False
    assert service._poll_task is None


@pytest.mark.asyncio
async def test_start_does_nothing_when_no_consent(
    store: EmailMonitorStore, service: EmailMonitorService
) -> None:
    """start() should be a no-op when consent is not granted."""
    store.save_settings(
        EmailMonitorSettings(enabled=True, consent_granted=False)
    )
    await service.start()
    assert service._running is False


@pytest.mark.asyncio
async def test_start_stop_lifecycle(
    store: EmailMonitorStore, service: EmailMonitorService
) -> None:
    """Starting and stopping the poll loop should work."""
    store.save_settings(
        EmailMonitorSettings(
            enabled=True, consent_granted=True, poll_interval_seconds=600
        )
    )
    await service.start()
    assert service._running is True
    assert service._poll_task is not None
    assert not service._poll_task.done()

    await service.stop()
    assert service._running is False
    assert service._poll_task is None


# ── Poll cycle tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poll_now_not_enabled(service: EmailMonitorService) -> None:
    """poll_now() should return early when not enabled."""
    result = await service.poll_now()
    assert result["success"] is False
    assert "Not enabled" in result.get("reason", "")


@pytest.mark.asyncio
async def test_poll_cycle_creates_todos(
    store: EmailMonitorStore,
    service: EmailMonitorService,
    fake_connector: FakeConnector,
    todo_service: TodoService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full poll cycle: fetch → extract → create todos."""
    # Setup store
    store.save_settings(
        EmailMonitorSettings(
            enabled=True,
            consent_granted=True,
            imap_host="fake",
            username="test@uni.edu",
            password="pw",
            mailbox="INBOX",
        )
    )

    # Inject fake connector
    monkeypatch.setattr(service, "_build_connector", lambda s=None: fake_connector)

    # Mock extractor to return controlled data
    async def fake_extract(msg: RawMessage) -> dict:
        return {
            "is_actionable": True,
            "summary": "Test summary",
            "items": [
                {
                    "title": "Test Assignment",
                    "due_at": None,
                    "due_at_confidence": None,
                    "kind": "assignment",
                    "course": "TEST101",
                    "priority": "normal",
                    "notes": "",
                }
            ],
        }

    import deeptutor.services.email_monitor.service as svc_mod

    monkeypatch.setattr(svc_mod, "extract_from_message", fake_extract)
    monkeypatch.setattr(svc_mod, "get_todo_service", lambda: todo_service)

    # Add a message to the fake connector
    fake_connector.add_message(
        RawMessage(
            uid="1",
            subject="Test Email",
            from_="prof@uni.edu",
            text_body="Assignment due next week",
            message_id="<msg1@test>",
        )
    )

    # Poll
    result = await service.poll_now()
    assert result["success"] is True, f"Poll failed: {result}"
    assert result["messages_fetched"] == 1
    assert result["todos_created"] >= 1
    assert service._poll_count == 1
    assert service._todos_created_count >= 1

    # Poll again — should be deduped via ledger
    result2 = await service.poll_now()
    assert result2["success"] is True
    assert result2["todos_created"] == 0
    assert result2["messages_fetched"] == 0  # no new UIDs


@pytest.mark.asyncio
async def test_poll_cycle_non_actionable_message(
    store: EmailMonitorStore,
    service: EmailMonitorService,
    fake_connector: FakeConnector,
    todo_service: TodoService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-actionable messages should get 'skipped_no_action' ledger entry."""
    store.save_settings(
        EmailMonitorSettings(
            enabled=True,
            consent_granted=True,
            imap_host="fake",
            username="test@uni.edu",
            password="pw",
            mailbox="INBOX",
        )
    )

    monkeypatch.setattr(service, "_build_connector", lambda s=None: fake_connector)

    async def fake_extract(msg: RawMessage) -> dict:
        return {"is_actionable": False, "summary": "Just info", "items": []}

    import deeptutor.services.email_monitor.service as svc_mod

    monkeypatch.setattr(svc_mod, "extract_from_message", fake_extract)
    monkeypatch.setattr(svc_mod, "get_todo_service", lambda: todo_service)

    fake_connector.add_message(
        RawMessage(
            uid="10",
            subject="Info Notice",
            from_="admin@uni.edu",
            text_body="Library hours changed",
            message_id="<info@test>",
        )
    )

    result = await service.poll_now()
    assert result["success"] is True
    assert result["todos_created"] == 0
    assert result["messages_fetched"] == 1

    # Check ledger entry was created with skipped status
    entries = store.get_ledger_entries(limit=5)
    assert any(e.status == "skipped_no_action" for e in entries)


@pytest.mark.asyncio
async def test_poll_cycle_connector_error(
    store: EmailMonitorStore,
    service: EmailMonitorService,
    fake_connector: FakeConnector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connector failure should be surfaced in the result."""
    store.save_settings(
        EmailMonitorSettings(
            enabled=True,
            consent_granted=True,
            imap_host="fake",
            username="test@uni.edu",
            password="pw",
            mailbox="INBOX",
        )
    )

    monkeypatch.setattr(service, "_build_connector", lambda s=None: fake_connector)
    fake_connector.should_fail = True
    fake_connector.fail_message = "IMAP connection timeout"

    result = await service.poll_now()
    assert result["success"] is False
    assert "error" in result
    assert "IMAP connection timeout" in result["error"]
    assert service._last_error is not None


# ── Status tests ─────────────────────────────────────────────────────


def test_get_status_when_not_started(service: EmailMonitorService) -> None:
    """get_status() should report sensible defaults when not running."""
    status = service.get_status()
    assert status["enabled"] is False  # default settings
    assert status["running"] is False
    assert status["poll_count"] == 0
    assert status["todos_created"] == 0
    assert status["last_poll_at"] is None
    assert status["last_error"] is None
    assert status["cursor"] is not None


@pytest.mark.asyncio
async def test_get_status_after_poll(
    store: EmailMonitorStore,
    service: EmailMonitorService,
    fake_connector: FakeConnector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_status() should reflect activity after a poll."""
    store.save_settings(
        EmailMonitorSettings(
            enabled=True,
            consent_granted=True,
            imap_host="fake",
            username="test@uni.edu",
            password="pw",
            mailbox="INBOX",
        )
    )

    monkeypatch.setattr(service, "_build_connector", lambda s=None: fake_connector)

    async def fake_extract(msg: RawMessage) -> dict:
        return {"is_actionable": False, "summary": "", "items": []}

    import deeptutor.services.email_monitor.service as svc_mod

    monkeypatch.setattr(svc_mod, "extract_from_message", fake_extract)

    fake_connector.add_message(
        RawMessage(uid="1", subject="Test", from_="a@b.com", text_body="Body")
    )

    await service.poll_now()

    status = service.get_status()
    assert status["poll_count"] == 1
    assert status["last_poll_at"] is not None
    assert status["last_error"] is None
    assert status["todos_created"] == 0


# ── Summarize tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summarize_returns_fallback_when_llm_unavailable(
    store: EmailMonitorStore,
    service: EmailMonitorService,
    fake_connector: FakeConnector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """summarize() should return a fallback digest when LLM fails."""
    store.save_settings(
        EmailMonitorSettings(
            enabled=True,
            consent_granted=True,
            imap_host="fake",
            username="test@uni.edu",
            password="pw",
            mailbox="INBOX",
        )
    )

    monkeypatch.setattr(service, "_build_connector", lambda s=None: fake_connector)

    fake_connector.add_message(
        RawMessage(
            uid="1",
            subject="Test",
            from_="a@b.com",
            text_body="Hello",
            date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
    )

    # Make generate_summary raise by monkeypatching the import inside summarizer
    import deeptutor.services.email_monitor.summarizer as summ_mod

    async def failing_summary(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(summ_mod, "generate_summary", failing_summary)

    # We need to re-patch the service module's reference too
    import deeptutor.services.email_monitor.service as svc_mod

    monkeypatch.setattr(svc_mod, "generate_summary", failing_summary)

    result = await service.summarize(since_days=7)
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_summarize_no_emails(
    store: EmailMonitorStore,
    service: EmailMonitorService,
    fake_connector: FakeConnector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """summarize() should handle the case of no emails gracefully."""
    store.save_settings(
        EmailMonitorSettings(
            enabled=True,
            consent_granted=True,
            imap_host="fake",
            username="test@uni.edu",
            password="pw",
            mailbox="INBOX",
        )
    )

    monkeypatch.setattr(service, "_build_connector", lambda s=None: fake_connector)

    # Override generate_summary to return fallback
    import deeptutor.services.email_monitor.service as svc_mod

    async def fake_summary(*args, **kwargs):
        return {
            "title": "Email Digest — test",
            "themes": [],
            "action_items": [],
            "noise_count": 0,
            "overall_summary": "No emails in this period.",
        }

    monkeypatch.setattr(svc_mod, "generate_summary", fake_summary)

    result = await service.summarize(since_days=1)
    assert result["success"] is True


# ── Singleton factory tests ──────────────────────────────────────────


def test_get_email_monitor_service_singleton() -> None:
    from deeptutor.services.email_monitor.service import (
        _service_instance,
        get_email_monitor_service,
    )

    # Reset for test isolation
    import deeptutor.services.email_monitor.service as svc_mod

    svc_mod._service_instance = None

    svc = get_email_monitor_service()
    assert svc is not None
    assert isinstance(svc, EmailMonitorService)

    svc2 = get_email_monitor_service()
    assert svc2 is svc  # same instance


def test_email_monitor_service_proxy() -> None:
    from deeptutor.services.email_monitor.service import email_monitor_service

    assert email_monitor_service is not None
    # The proxy should delegate method access to the singleton
    status = email_monitor_service.get_status()
    assert isinstance(status, dict)


@pytest.mark.asyncio
async def test_double_start_is_noop(
    store: EmailMonitorStore, service: EmailMonitorService
) -> None:
    """Calling start() twice should not create two poll loops."""
    store.save_settings(
        EmailMonitorSettings(
            enabled=True, consent_granted=True, poll_interval_seconds=600
        )
    )
    await service.start()
    task1 = service._poll_task
    await service.start()  # second call
    assert service._poll_task is task1  # same task

    await service.stop()
