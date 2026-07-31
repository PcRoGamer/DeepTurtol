"""Pydantic models for the email monitor feature."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EmailMonitorSettings(BaseModel):
    """Persisted to data/user/settings/email_monitor.json"""

    enabled: bool = False
    imap_host: str = "outlook.office365.com"
    imap_port: int = 993
    imap_use_ssl: bool = True
    username: str = ""
    password: str = ""  # masked in API responses
    mailbox: str = "INBOX"
    poll_interval_seconds: int = 300  # min 60
    sender_filter: str = ""  # optional glob like *@unimelb.edu.au
    subject_filter: str = ""  # optional keyword like assignment
    mark_seen: bool = False  # use BODY.PEEK[] by default
    consent_granted: bool = False
    auth_mode: Literal["imap", "graph"] = "imap"  # graph is stub for v2
    bootstrap_last_n: int = 0  # 0 = don't bootstrap; max 50


class RawMessage(BaseModel):
    """Represents a fetched email before LLM extraction."""

    model_config = {"populate_by_name": True}

    message_id: str | None = None  # RFC 822 Message-ID header
    uid: str  # IMAP UID
    subject: str
    from_: str = Field(alias="from")
    to: list[str] = []
    date: datetime | None = None
    text_body: str
    html_body: str | None = None
    headers: dict[str, str] = {}  # key raw headers for fallback dedup


class MailCursor(BaseModel):
    """Persistent cursor for incremental polling."""

    last_uid: int = 0
    last_poll_at: float = 0.0  # time.time()
    uidvalidity: int | None = None  # detect mailbox reset


class LedgerEntry(BaseModel):
    """One entry in the processed.jsonl ledger."""

    ledger_id: str  # f"{account_fingerprint}:{message_key}"
    message_uid: str
    message_id: str | None
    subject: str
    status: Literal["processed", "skipped_no_action", "error"]
    error_message: str = ""
    processed_at: float  # time.time()
    created_todo_ids: list[str] = []


class ConnectionResult(BaseModel):
    """Result of an IMAP connection attempt."""

    success: bool
    message: str = ""
    folder_info: str | None = None  # UIDVALIDITY, EXISTS, etc.
