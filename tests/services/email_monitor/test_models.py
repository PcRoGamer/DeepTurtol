"""Tests for email monitor Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

from deeptutor.services.email_monitor.models import (
    ConnectionResult,
    EmailMonitorSettings,
    LedgerEntry,
    MailCursor,
    RawMessage,
)


def test_email_monitor_settings_defaults() -> None:
    settings = EmailMonitorSettings()
    assert settings.enabled is False
    assert settings.imap_host == "outlook.office365.com"
    assert settings.imap_port == 993
    assert settings.imap_use_ssl is True
    assert settings.username == ""
    assert settings.password == ""
    assert settings.mailbox == "INBOX"
    assert settings.poll_interval_seconds == 300
    assert settings.sender_filter == ""
    assert settings.subject_filter == ""
    assert settings.mark_seen is False
    assert settings.consent_granted is False
    assert settings.auth_mode == "imap"
    assert settings.bootstrap_last_n == 0


def test_email_monitor_settings_custom_values() -> None:
    settings = EmailMonitorSettings(
        enabled=True,
        imap_host="imap.gmail.com",
        imap_port=993,
        username="test@example.com",
        password="secret",
        poll_interval_seconds=120,
        sender_filter="*@example.com",
        subject_filter="alert",
        mark_seen=True,
        consent_granted=True,
        auth_mode="graph",
        bootstrap_last_n=10,
    )
    assert settings.enabled is True
    assert settings.imap_host == "imap.gmail.com"
    assert settings.username == "test@example.com"
    assert settings.password == "secret"
    assert settings.poll_interval_seconds == 120
    assert settings.auth_mode == "graph"
    assert settings.bootstrap_last_n == 10


def test_raw_message_from_alias() -> None:
    msg = RawMessage(
        uid="12345",
        subject="Test",
        from_="sender@example.com",
        text_body="Hello",
    )
    assert msg.from_ == "sender@example.com"
    assert msg.model_dump(by_alias=True)["from"] == "sender@example.com"


def test_raw_message_defaults() -> None:
    msg = RawMessage(
        uid="42",
        subject="No Body",
        from_="a@b.com",
        text_body="",
    )
    assert msg.message_id is None
    assert msg.to == []
    assert msg.date is None
    assert msg.html_body is None
    assert msg.headers == {}


def test_raw_message_with_all_fields() -> None:
    dt = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    msg = RawMessage(
        message_id="<abc123@mail.example.com>",
        uid="999",
        subject="Full Message",
        from_="alice@example.com",
        to=["bob@example.com"],
        date=dt,
        text_body="Hi Bob",
        html_body="<p>Hi Bob</p>",
        headers={"Message-ID": "<abc123@mail.example.com>"},
    )
    assert msg.message_id == "<abc123@mail.example.com>"
    assert msg.uid == "999"
    assert msg.date == dt
    assert msg.to == ["bob@example.com"]
    assert msg.html_body == "<p>Hi Bob</p>"
    assert msg.headers["Message-ID"] == "<abc123@mail.example.com>"


def test_mail_cursor_defaults() -> None:
    cursor = MailCursor()
    assert cursor.last_uid == 0
    assert cursor.last_poll_at == 0.0
    assert cursor.uidvalidity is None


def test_mail_cursor_custom_values() -> None:
    cursor = MailCursor(last_uid=100, last_poll_at=1234567890.0, uidvalidity=42)
    assert cursor.last_uid == 100
    assert cursor.last_poll_at == 1234567890.0
    assert cursor.uidvalidity == 42


def test_ledger_entry_minimal() -> None:
    entry = LedgerEntry(
        ledger_id="abc123:def456",
        message_uid="42",
        message_id="<msg@id>",
        subject="Test",
        status="processed",
        processed_at=1000.0,
    )
    assert entry.ledger_id == "abc123:def456"
    assert entry.message_uid == "42"
    assert entry.message_id == "<msg@id>"
    assert entry.status == "processed"
    assert entry.error_message == ""
    assert entry.created_todo_ids == []


def test_ledger_entry_with_error() -> None:
    entry = LedgerEntry(
        ledger_id="abc:def",
        message_uid="99",
        message_id=None,
        subject="Failed",
        status="error",
        error_message="Connection timeout",
        processed_at=2000.0,
        created_todo_ids=["todo1"],
    )
    assert entry.status == "error"
    assert entry.error_message == "Connection timeout"
    assert entry.created_todo_ids == ["todo1"]


def test_connection_result_defaults() -> None:
    result = ConnectionResult(success=True)
    assert result.success is True
    assert result.message == ""
    assert result.folder_info is None


def test_connection_result_with_info() -> None:
    result = ConnectionResult(
        success=False,
        message="Authentication failed",
        folder_info="UIDVALIDITY 42, EXISTS 0",
    )
    assert result.success is False
    assert result.message == "Authentication failed"
    assert result.folder_info == "UIDVALIDITY 42, EXISTS 0"
