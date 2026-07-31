"""Persistent store for email monitor: settings, processed ledger, cursor, and summary cache."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from deeptutor.services.path_service import get_path_service

from .models import EmailMonitorSettings, LedgerEntry, MailCursor


def _compute_account_fingerprint(imap_host: str, username: str, mailbox: str) -> str:
    """16-char hex fingerprint from account identity."""
    raw = f"{imap_host}|{username}|{mailbox}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _compute_message_key(message_id: str | None, uid: str, headers: dict[str, str], subject: str, date: str | None) -> str:
    """Produce a deterministic message key for ledger ID generation."""
    if message_id:
        return message_id
    if uid:
        return f"uid:{uid}"
    raw_headers = json.dumps(headers, sort_keys=True, ensure_ascii=False)
    date_str = date or ""
    fallback = hashlib.sha256(
        f"{raw_headers}|{subject}|{date_str}".encode("utf-8")
    ).hexdigest()[:16]
    return f"hash:{fallback}"


def make_ledger_id(
    imap_host: str,
    username: str,
    mailbox: str,
    message_id: str | None,
    uid: str,
    headers: dict[str, str] | None = None,
    subject: str = "",
    date: str | None = None,
) -> str:
    """Build a ledger ID from account identity and message identity."""
    fingerprint = _compute_account_fingerprint(imap_host, username, mailbox)
    msg_key = _compute_message_key(message_id, uid, headers or {}, subject, date)
    return f"{fingerprint}:{msg_key}"


class EmailMonitorStore:
    """Manages settings, processed-email ledger, cursor, and summary cache.

    Mirrors the ``NotebookManager`` singleton factory pattern.
    """

    def __init__(self, base_dir: str | None = None, settings_dir: str | None = None):
        if base_dir is None:
            path_service = get_path_service()
            base_dir_path = path_service.get_workspace_feature_dir("email_monitor")
        else:
            base_dir_path = Path(base_dir)

        if settings_dir is None:
            path_service = get_path_service()
            settings_dir_path = path_service.get_settings_dir()
        else:
            settings_dir_path = Path(settings_dir)

        self.base_dir = base_dir_path
        self.settings_dir = settings_dir_path

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.settings_dir.mkdir(parents=True, exist_ok=True)

        # Ledger
        self.ledger_file = self.base_dir / "processed.jsonl"

        # Cursor
        self.cursor_file = self.base_dir / "cursor.json"

        # Summary cache
        self.summaries_dir = self.base_dir / "summaries"
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

        # In-memory set of processed ledger IDs for fast lookups
        self._processed_ids: set[str] | None = None

    # ── Settings ────────────────────────────────────────────────────────

    def _settings_path(self) -> Path:
        return self.settings_dir / "email_monitor.json"

    def load_settings(self) -> EmailMonitorSettings:
        """Load settings from the JSON settings file."""
        path = self._settings_path()
        if not path.exists():
            return EmailMonitorSettings()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return EmailMonitorSettings(**data)
        except Exception:
            return EmailMonitorSettings()

    def save_settings(self, settings: EmailMonitorSettings) -> None:
        """Persist settings to the JSON settings file."""
        path = self._settings_path()
        data = settings.model_dump()
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def get_settings(self) -> EmailMonitorSettings:
        """Return cached settings (loads from file on first call)."""
        if not hasattr(self, "_settings_cache"):
            self._settings_cache = self.load_settings()
        return self._settings_cache

    @staticmethod
    def mask_password(settings: EmailMonitorSettings) -> dict[str, Any]:
        """Return settings dict with password masked."""
        data = settings.model_dump()
        if data.get("password"):
            data["password"] = "********"
        return data

    # ── Processed Ledger ────────────────────────────────────────────────

    def _load_processed_ids(self) -> set[str]:
        """Load all ledger IDs from the JSONL file into memory."""
        if self._processed_ids is not None:
            return self._processed_ids
        ids: set[str] = set()
        if self.ledger_file.exists():
            for line in self.ledger_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    lid = entry.get("ledger_id")
                    if lid:
                        ids.add(lid)
                except json.JSONDecodeError:
                    continue
        self._processed_ids = ids
        return ids

    def is_processed(self, ledger_id: str) -> bool:
        """Check whether the given ledger ID has been processed."""
        return ledger_id in self._load_processed_ids()

    def mark_processed(self, entry: LedgerEntry) -> None:
        """Append a ledger entry to the JSONL file and update the in-memory set."""
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
        # Load processed IDs into memory and add the new one
        ids = self._load_processed_ids()
        ids.add(entry.ledger_id)

    def get_ledger_entries(self, limit: int = 100) -> list[LedgerEntry]:
        """Return the most recent *limit* ledger entries."""
        if not self.ledger_file.exists():
            return []
        lines = self.ledger_file.read_text(encoding="utf-8").splitlines()
        entries: list[LedgerEntry] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(LedgerEntry(**json.loads(line)))
            except Exception:
                continue
        return entries[-limit:]

    def count_processed(self) -> int:
        """Return total number of processed entries."""
        return len(self._load_processed_ids())

    # ── Cursor ──────────────────────────────────────────────────────────

    def load_cursor(self) -> MailCursor:
        """Load cursor from JSON file, returning defaults if missing."""
        if not self.cursor_file.exists():
            return MailCursor()
        try:
            data = json.loads(self.cursor_file.read_text(encoding="utf-8"))
            return MailCursor(**data)
        except Exception:
            return MailCursor()

    def save_cursor(self, cursor: MailCursor) -> None:
        """Persist cursor to JSON file."""
        self.cursor_file.write_text(
            cursor.model_dump_json(indent=2), encoding="utf-8"
        )

    # ── Summary Cache ───────────────────────────────────────────────────

    def save_summary(self, date_str: str, summary_data: dict) -> None:
        """Save a summary JSON for a given date string."""
        path = self.summaries_dir / f"{date_str}.json"
        path.write_text(
            json.dumps(summary_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def load_summary(self, date_str: str) -> dict | None:
        """Load a summary JSON for a given date string, or None."""
        path = self.summaries_dir / f"{date_str}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def list_summaries(self) -> list[str]:
        """Return sorted date strings for available summaries."""
        if not self.summaries_dir.exists():
            return []
        dates: list[str] = []
        for f in sorted(self.summaries_dir.iterdir()):
            if f.suffix == ".json":
                dates.append(f.stem)
        return dates


_instances: dict[str, EmailMonitorStore] = {}


def get_email_monitor_store() -> EmailMonitorStore:
    """Return the singleton ``EmailMonitorStore``, cached by base_dir."""
    path_service = get_path_service()
    base_dir = path_service.get_workspace_feature_dir("email_monitor")
    key = str(base_dir.resolve())
    if key not in _instances:
        _instances[key] = EmailMonitorStore(base_dir=str(base_dir))
    return _instances[key]


class _EmailMonitorStoreProxy:
    """Proxy that delegates attribute access to the singleton store."""

    def __getattr__(self, name: str):
        return getattr(get_email_monitor_store(), name)


email_monitor_store = _EmailMonitorStoreProxy()
