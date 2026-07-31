"""Email connector protocol definition."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from deeptutor.services.email_monitor.models import ConnectionResult, MailCursor, RawMessage


class EmailConnector(Protocol):
    """Protocol for email connectors (IMAP, Graph API, fake, etc.)."""

    def list_new_messages(
        self, cursor: MailCursor
    ) -> tuple[list[RawMessage], MailCursor]:
        """Fetch messages with UID > cursor.last_uid.

        Returns (messages, new_cursor).
        """
        ...

    def fetch_range(
        self, since: datetime, until: datetime, limit: int = 50
    ) -> list[RawMessage]:
        """Fetch messages within a date range (for summaries)."""
        ...

    def test_connection(self) -> ConnectionResult:
        """Test IMAP login and return result."""
        ...
