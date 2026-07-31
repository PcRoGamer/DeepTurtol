"""In-memory fake connector for testing the email monitor.

Provides a ``FakeConnector`` that simulates an IMAP mailbox without
network access. Add messages via ``add_message()``, control failure
modes via ``should_fail`` / ``fail_message``.
"""

from __future__ import annotations

import time
from datetime import datetime

from deeptutor.services.email_monitor.models import ConnectionResult, MailCursor, RawMessage


class FakeConnector:
    """In-memory fake connector for testing email monitoring logic.

    Usage::

        connector = FakeConnector()
        connector.add_message(RawMessage(uid="1", subject="Test", from_="a@b.com", text_body="Hello"))
        msgs, cursor = connector.list_new_messages(MailCursor())
    """

    def __init__(self) -> None:
        self.messages: list[RawMessage] = []
        self.cursor = MailCursor()
        self.should_fail = False
        self.fail_message = ""

    def add_message(self, msg: RawMessage) -> None:
        """Add a message to the fake mailbox."""
        self.messages.append(msg)

    def list_new_messages(
        self, cursor: MailCursor
    ) -> tuple[list[RawMessage], MailCursor]:
        """Return messages with UID > cursor.last_uid.

        Respects ``should_fail`` for simulating connection errors.
        """
        if self.should_fail:
            raise ConnectionError(self.fail_message)

        new = [m for m in self.messages if int(m.uid) > cursor.last_uid]
        new_cursor = MailCursor(
            last_uid=max(
                (int(m.uid) for m in self.messages),
                default=cursor.last_uid,
            ),
            last_poll_at=time.time(),
        )
        return new, new_cursor

    def fetch_range(
        self, since: datetime, until: datetime, limit: int = 50
    ) -> list[RawMessage]:
        """Return messages within a date range."""
        if self.should_fail:
            raise ConnectionError(self.fail_message)

        result: list[RawMessage] = []
        for m in self.messages:
            if m.date and since <= m.date <= until:
                result.append(m)
        return result[:limit]

    def test_connection(self) -> ConnectionResult:
        """Simulate connection test."""
        if self.should_fail:
            return ConnectionResult(success=False, message=self.fail_message)
        return ConnectionResult(
            success=True,
            folder_info="Fake INBOX (100 messages)",
        )
