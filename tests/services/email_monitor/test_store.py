"""Tests for EmailMonitorStore persistence layer."""

from __future__ import annotations

import json
import time
from pathlib import Path

from deeptutor.services.email_monitor.models import (
    EmailMonitorSettings,
    LedgerEntry,
    MailCursor,
)
from deeptutor.services.email_monitor.store import (
    EmailMonitorStore,
    _compute_account_fingerprint,
    _compute_message_key,
    make_ledger_id,
)


def test_settings_roundtrip(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    # Default settings
    default = store.load_settings()
    assert default.enabled is False

    # Save custom settings
    custom = EmailMonitorSettings(
        enabled=True,
        imap_host="imap.gmail.com",
        username="test@example.com",
        password="s3cret",
        mailbox="INBOX",
        poll_interval_seconds=120,
        sender_filter="*@example.com",
        subject_filter="alert",
        bootstrap_last_n=10,
    )
    store.save_settings(custom)

    # Reload
    loaded = store.load_settings()
    assert loaded.enabled is True
    assert loaded.imap_host == "imap.gmail.com"
    assert loaded.username == "test@example.com"
    assert loaded.password == "s3cret"
    assert loaded.poll_interval_seconds == 120
    assert loaded.sender_filter == "*@example.com"
    assert loaded.bootstrap_last_n == 10


def test_settings_get_cached(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    # First call should return defaults and cache
    s1 = store.get_settings()
    assert s1.enabled is False

    # Second call returns cached version (even though file doesn't exist)
    s2 = store.get_settings()
    assert s2.enabled is False
    assert s2 is s1  # same object reference due to caching


def test_settings_get_uses_json_fallback(tmp_path: Path) -> None:
    """get_settings() should load from file when cache is empty."""
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    # Write settings.json directly
    (settings_dir / "email_monitor.json").write_text(
        json.dumps({"enabled": True, "username": "direct@test.com"}), encoding="utf-8"
    )

    # Fresh store should load from file
    store2 = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))
    loaded = store2.get_settings()
    assert loaded.enabled is True
    assert loaded.username == "direct@test.com"


def test_password_masking(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    # With password
    s1 = EmailMonitorSettings(password="s3cret")
    masked = store.mask_password(s1)
    assert masked["password"] == "********"

    # Without password
    s2 = EmailMonitorSettings(password="")
    masked2 = store.mask_password(s2)
    assert masked2["password"] == ""


def test_ledger_is_processed_unknown(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    assert store.is_processed("nonexistent:id") is False


def test_ledger_mark_and_check(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    entry = LedgerEntry(
        ledger_id="acct:msg1",
        message_uid="100",
        message_id="<msg1@id>",
        subject="Test email",
        status="processed",
        processed_at=time.time(),
    )
    store.mark_processed(entry)

    assert store.is_processed("acct:msg1") is True
    assert store.is_processed("acct:msg2") is False


def test_ledger_no_double_count(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    entry = LedgerEntry(
        ledger_id="acct:dup",
        message_uid="101",
        message_id="<dup@id>",
        subject="Duplicate test",
        status="processed",
        processed_at=time.time(),
    )
    store.mark_processed(entry)
    store.mark_processed(entry)

    assert store.count_processed() == 1


def test_ledger_count(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    assert store.count_processed() == 0

    for i in range(5):
        entry = LedgerEntry(
            ledger_id=f"acct:msg{i}",
            message_uid=str(200 + i),
            message_id=f"<msg{i}@id>",
            subject=f"Email {i}",
            status="processed",
            processed_at=time.time(),
        )
        store.mark_processed(entry)

    assert store.count_processed() == 5


def test_ledger_get_entries(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    for i in range(10):
        entry = LedgerEntry(
            ledger_id=f"acct:msg{i}",
            message_uid=str(300 + i),
            message_id=None,
            subject=f"Email {i}",
            status="processed",
            processed_at=float(i),
        )
        store.mark_processed(entry)

    entries = store.get_ledger_entries(limit=3)
    assert len(entries) == 3
    assert entries[0].subject == "Email 7"


def test_ledger_get_entries_empty(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    assert store.get_ledger_entries() == []


def test_cursor_save_load_roundtrip(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    cursor = MailCursor(last_uid=250, last_poll_at=1234567890.0, uidvalidity=99)
    store.save_cursor(cursor)

    loaded = store.load_cursor()
    assert loaded.last_uid == 250
    assert loaded.last_poll_at == 1234567890.0
    assert loaded.uidvalidity == 99


def test_cursor_defaults_when_missing(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    cursor = store.load_cursor()
    assert cursor.last_uid == 0
    assert cursor.last_poll_at == 0.0
    assert cursor.uidvalidity is None


def test_summary_save_load(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    data = {"emails_processed": 5, "todos_created": 2}
    store.save_summary("2025-06-15", data)

    loaded = store.load_summary("2025-06-15")
    assert loaded is not None
    assert loaded["emails_processed"] == 5
    assert loaded["todos_created"] == 2


def test_summary_load_missing(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    result = store.load_summary("2099-01-01")
    assert result is None


def test_summary_list(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    store.save_summary("2025-06-15", {"a": 1})
    store.save_summary("2025-06-14", {"b": 2})
    store.save_summary("2025-06-16", {"c": 3})

    dates = store.list_summaries()
    assert dates == ["2025-06-14", "2025-06-15", "2025-06-16"]


def test_summary_list_empty(tmp_path: Path) -> None:
    base = tmp_path / "email_monitor"
    settings_dir = tmp_path / "settings"
    store = EmailMonitorStore(base_dir=str(base), settings_dir=str(settings_dir))

    assert store.list_summaries() == []


def test_make_ledger_id_with_message_id() -> None:
    lid = make_ledger_id(
        imap_host="outlook.office365.com",
        username="user@university.edu",
        mailbox="INBOX",
        message_id="<abc123@mail>",
        uid="500",
    )
    assert "<abc123@mail>" in lid
    assert lid.endswith(":<abc123@mail>")


def test_make_ledger_id_with_uid_fallback() -> None:
    lid = make_ledger_id(
        imap_host="outlook.office365.com",
        username="user@university.edu",
        mailbox="INBOX",
        message_id=None,
        uid="500",
    )
    assert lid.endswith(":uid:500")


def test_make_ledger_id_hash_fallback() -> None:
    lid = make_ledger_id(
        imap_host="outlook.office365.com",
        username="user@university.edu",
        mailbox="INBOX",
        message_id=None,
        uid="",
        headers={"From": "a@b.com"},
        subject="Test",
        date="2025-01-01",
    )
    assert lid.startswith("hash:") is False  # starts with fingerprint:
    assert ":hash:" in lid


def test_account_fingerprint_consistent() -> None:
    fp1 = _compute_account_fingerprint("imap.a.com", "u1", "INBOX")
    fp2 = _compute_account_fingerprint("imap.a.com", "u1", "INBOX")
    assert fp1 == fp2
    assert len(fp1) == 16


def test_account_fingerprint_different() -> None:
    fp1 = _compute_account_fingerprint("imap.a.com", "u1", "INBOX")
    fp2 = _compute_account_fingerprint("imap.b.com", "u1", "INBOX")
    assert fp1 != fp2


def test_message_key_uses_message_id_when_present() -> None:
    key = _compute_message_key("<msg@id>", "500", {}, "Sub", "date")
    assert key == "<msg@id>"


def test_message_key_uid_fallback() -> None:
    key = _compute_message_key(None, "500", {}, "Sub", "date")
    assert key == "uid:500"


def test_message_key_hash_fallback() -> None:
    key = _compute_message_key(None, "", {}, "Sub", "date")
    assert key.startswith("hash:")
    assert len(key) == 5 + 16  # "hash:" (5 chars) + 16 hex chars
