"""EmailMonitorService — poll university inbox, extract todos via LLM, manage lifecycle."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from deeptutor.services.email_monitor.connectors.imap import ImapConnector
from deeptutor.services.email_monitor.extractor import extract_from_message
from deeptutor.services.email_monitor.models import (
    ConnectionResult,
    EmailMonitorSettings,
    LedgerEntry,
    MailCursor,
    RawMessage,
)
from deeptutor.services.email_monitor.store import (
    EmailMonitorStore,
    get_email_monitor_store,
    make_ledger_id,
)
from deeptutor.services.email_monitor.summarizer import generate_summary
from deeptutor.services.todos import get_todo_service

logger = logging.getLogger(__name__)


class EmailMonitorService:
    """Poll university inbox, extract todos via LLM, manage lifecycle."""

    def __init__(self, store: EmailMonitorStore | None = None):
        self.store = store or get_email_monitor_store()
        self._running = False
        self._poll_task: asyncio.Task | None = None
        self._poll_lock = asyncio.Lock()
        self._last_error: str | None = None
        self._last_poll_at: float | None = None
        self._poll_count: int = 0
        self._todos_created_count: int = 0

    def _build_connector(
        self, settings: EmailMonitorSettings | None = None
    ) -> ImapConnector:
        """Create an ImapConnector from current settings."""
        s = settings or self.store.get_settings()
        return ImapConnector(s)

    async def start(self) -> None:
        """Start the background poll loop if enabled."""
        settings = self.store.get_settings()
        if not settings.enabled or not settings.consent_granted:
            logger.info(
                "Email monitor not enabled or consent not granted — not starting"
            )
            return

        if self._running:
            logger.warning("Email monitor already running")
            return

        self._running = True
        self._poll_task = asyncio.create_task(
            self._poll_loop(),
            name="email-monitor:poll",
        )
        logger.info("Email monitor poll loop started")

    async def stop(self) -> None:
        """Stop the background poll loop."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except (asyncio.CancelledError, Exception):
                pass
            self._poll_task = None
        logger.info("Email monitor poll loop stopped")

    async def poll_now(self) -> dict[str, Any]:
        """Trigger a single poll cycle (used by API 'Check now')."""
        async with self._poll_lock:
            return await self._poll_once()

    async def summarize(
        self, since_days: int = 1, mailbox: str | None = None
    ) -> dict[str, Any]:
        """Generate an on-demand summary of recent emails (no todo creation)."""
        settings = self.store.get_settings()
        connector = self._build_connector(settings)

        until = datetime.now(timezone.utc)
        since = until - timedelta(days=since_days)

        try:
            messages = await asyncio.to_thread(
                connector.fetch_range, since, until, limit=100
            )
        except Exception as e:
            logger.error("Failed to fetch messages for summary: %s", e)
            return {"success": False, "error": str(e)}

        date_label = f"{since.date().isoformat()} to {until.date().isoformat()}"
        try:
            digest = await generate_summary(messages, date_label)
        except Exception as e:
            logger.error("Failed to generate summary: %s", e)
            return {"success": False, "error": str(e)}

        # Cache the summary
        date_key = until.date().isoformat()
        self.store.save_summary(f"digest-{date_key}", digest)

        return {"success": True, "summary": digest, "message_count": len(messages)}

    def get_status(self) -> dict[str, Any]:
        """Return current status."""
        settings = self.store.get_settings()
        cursor = self.store.load_cursor()
        return {
            "enabled": settings.enabled,
            "consent_granted": settings.consent_granted,
            "last_poll_at": self._last_poll_at,
            "last_error": self._last_error,
            "poll_count": self._poll_count,
            "todos_created": self._todos_created_count,
            "cursor": cursor.model_dump(mode="json"),
            "running": self._running,
        }

    # ── Poll loop ───────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Background poll loop."""
        while self._running:
            try:
                settings = self.store.get_settings()
                interval = max(settings.poll_interval_seconds, 60)

                async with self._poll_lock:
                    await self._poll_once()

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Poll loop error: %s", e, exc_info=True)
                self._last_error = str(e)
                await asyncio.sleep(60)

    async def _poll_once(self) -> dict[str, Any]:
        """One poll cycle: fetch → extract → create todos → update ledger."""
        settings = self.store.get_settings()
        if not settings.enabled or not settings.consent_granted:
            return {"success": False, "reason": "Not enabled or consent not granted"}

        connector = self._build_connector(settings)
        cursor = self.store.load_cursor()

        result: dict[str, Any] = {
            "success": True,
            "messages_fetched": 0,
            "todos_created": 0,
            "errors": [],
        }

        try:
            messages, new_cursor = await asyncio.to_thread(
                connector.list_new_messages, cursor
            )
        except Exception as e:
            error = f"IMAP fetch failed: {e}"
            logger.error(error)
            self._last_error = error
            return {"success": False, "error": error}

        result["messages_fetched"] = len(messages)

        todo_service = get_todo_service()
        for msg in messages:
            # Build ledger ID
            headers_dict = msg.headers or {}
            ledger_id = make_ledger_id(
                imap_host=settings.imap_host,
                username=settings.username,
                mailbox=settings.mailbox,
                message_id=msg.message_id,
                uid=msg.uid,
                headers=headers_dict,
                subject=msg.subject,
                date=msg.date.isoformat() if msg.date else None,
            )

            # Skip if already processed
            if self.store.is_processed(ledger_id):
                continue

            try:
                # LLM extraction
                extracted = await extract_from_message(msg)

                if extracted.get("is_actionable") and extracted.get("items"):
                    created_ids = []
                    for item_data in extracted["items"]:
                        # Secondary dedup check
                        title = item_data.get("title", "")
                        existing = todo_service.find_by_source(
                            source_message_id=msg.message_id or f"uid:{msg.uid}",
                            normalized_title=title,
                        )
                        if existing:
                            logger.info("Skipping duplicate todo: %s", title)
                            continue

                        # Create todo
                        todo = todo_service.create_item(
                            {
                                "title": title,
                                "due_at": item_data.get("due_at"),
                                "due_at_confidence": item_data.get("due_at_confidence"),
                                "kind": item_data.get("kind", "other"),
                                "course": item_data.get("course"),
                                "priority": item_data.get("priority", "normal"),
                                "notes": item_data.get("notes", ""),
                                "source": "email",
                                "source_message_id": msg.message_id
                                or f"uid:{msg.uid}",
                                "source_subject": msg.subject,
                                "source_from": msg.from_,
                                "source_received_at": msg.date,
                            }
                        )
                        created_ids.append(todo.id)

                    entry_status = "processed" if created_ids else "skipped_no_action"
                else:
                    entry_status = "skipped_no_action"
                    created_ids = []

                # Record in ledger
                self.store.mark_processed(
                    LedgerEntry(
                        ledger_id=ledger_id,
                        message_uid=msg.uid,
                        message_id=msg.message_id,
                        subject=msg.subject,
                        status=entry_status,
                        processed_at=time.time(),
                        created_todo_ids=created_ids,
                    )
                )

                result["todos_created"] += len(created_ids)

            except Exception as e:
                error = f"Failed to process message {msg.uid}: {e}"
                logger.warning(error)
                result["errors"].append(error)
                self.store.mark_processed(
                    LedgerEntry(
                        ledger_id=ledger_id,
                        message_uid=msg.uid,
                        message_id=msg.message_id,
                        subject=msg.subject,
                        status="error",
                        error_message=str(e),
                        processed_at=time.time(),
                    )
                )

        # Save cursor
        new_cursor.last_poll_at = time.time()
        self.store.save_cursor(new_cursor)

        # Update service state
        self._last_poll_at = time.time()
        self._last_error = None
        self._poll_count += 1
        self._todos_created_count += result["todos_created"]

        return result


# ── Singleton factory (mirrors other services) ─────────────────────

_service_instance: EmailMonitorService | None = None


def get_email_monitor_service() -> EmailMonitorService:
    global _service_instance
    if _service_instance is None:
        _service_instance = EmailMonitorService()
    return _service_instance


class _EmailMonitorServiceProxy:
    """Convenience proxy so callers can write ``email_monitor_service.poll_now()``."""

    def __getattr__(self, name: str):
        return getattr(get_email_monitor_service(), name)


email_monitor_service: EmailMonitorService = _EmailMonitorServiceProxy()  # type: ignore[assignment]
