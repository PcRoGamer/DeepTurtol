"""IMAP email connector.

Fetches emails from Microsoft 365 (or any IMAP server) using the ``imaplib``
stdlib module. Patterns adapted from ``deeptutor/partners/channels/email.py``.
"""

from __future__ import annotations

import imaplib
import re
import time
from datetime import datetime
from email import policy
from email.parser import BytesParser
from typing import Any

from deeptutor.services.email_monitor.connectors.parse_utils import (
    decode_header_value,
    extract_text_body,
)
from deeptutor.services.email_monitor.models import (
    ConnectionResult,
    EmailMonitorSettings,
    MailCursor,
    RawMessage,
)

# Month abbreviations for IMAP date formatting
_IMAP_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _format_imap_date(dt: datetime) -> str:
    """Format a datetime for IMAP SEARCH (always English month abbreviations)."""
    month = _IMAP_MONTHS[dt.month - 1]
    return f"{dt.day:02d}-{month}-{dt.year}"


class ImapConnector:
    """Connector that fetches emails from an IMAP server.

    Args:
        settings: Email monitor settings with IMAP host, credentials, etc.
    """

    def __init__(self, settings: EmailMonitorSettings) -> None:
        self.settings = settings
        self._host = settings.imap_host
        self._port = settings.imap_port
        self._use_ssl = settings.imap_use_ssl
        self._username = settings.username
        self._password = settings.password
        self._mailbox = settings.mailbox or "INBOX"
        self._mark_seen = settings.mark_seen

    # ── Connection management ────────────────────────────────────────────

    def _connect(self) -> imaplib.IMAP4:
        """Open a new IMAP connection, login, and select the mailbox.

        Returns:
            Connected and selected IMAP client instance.

        Raises:
            ConnectionError: If connection, login, or select fails.
        """
        try:
            if self._use_ssl:
                client: imaplib.IMAP4 = imaplib.IMAP4_SSL(
                    self._host, self._port
                )
            else:
                client = imaplib.IMAP4(self._host, self._port)

            client.login(self._username, self._password)
            status, data = client.select(self._mailbox)
            if status != "OK":
                raise ConnectionError(
                    f"IMAP SELECT failed for mailbox {self._mailbox!r}: {data}"
                )
            return client
        except (imaplib.IMAP4.error, OSError) as e:
            raise ConnectionError(f"IMAP connection failed: {e}") from e

    @staticmethod
    def _extract_message_bytes(fetched: list[Any]) -> bytes | None:
        """Extract raw message bytes from an IMAP fetch response."""
        for item in fetched:
            if (
                isinstance(item, tuple)
                and len(item) >= 2
                and isinstance(item[1], (bytes, bytearray))
            ):
                return bytes(item[1])
        return None

    @staticmethod
    def _extract_uid(fetched: list[Any]) -> str:
        """Extract UID string from IMAP fetch response."""
        for item in fetched:
            if isinstance(item, tuple) and item and isinstance(item[0], (bytes, bytearray)):
                head = bytes(item[0]).decode("utf-8", errors="ignore")
                m = re.search(r"UID\s+(\d+)", head)
                if m:
                    return m.group(1)
        return ""

    @staticmethod
    def _get_uidvalidity(select_data: list[bytes]) -> int | None:
        """Extract UIDVALIDITY from IMAP SELECT response.

        IMAP SELECT returns responses that include ``* OK [UIDVALIDITY <n>]``.
        """
        for item in select_data:
            if isinstance(item, bytes):
                decoded = item.decode("utf-8", errors="ignore")
                m = re.search(r"UIDVALIDITY\s+(\d+)", decoded)
                if m:
                    return int(m.group(1))
        return None

    # ── Core operations ──────────────────────────────────────────────────

    def list_new_messages(
        self, cursor: MailCursor
    ) -> tuple[list[RawMessage], MailCursor]:
        """Fetch messages with UID > cursor.last_uid.

        Uses ``UID SEARCH`` for incremental fetching. If the mailbox
        UIDVALIDITY has changed (or cursor has none), the new UIDVALIDITY
        is recorded; no automatic re-fetch is triggered — the caller
        should handle reset logic.

        Returns:
            (messages, new_cursor) tuple.
        """
        messages: list[RawMessage] = []
        client = self._connect()

        try:
            # Check UIDVALIDITY
            uidvalidity = self._get_uidvalidity(client.response("UIDVALIDITY")[1])
            if uidvalidity is None:
                # If UIDVALIDITY not in response, fetch it explicitly
                status, data = client.select(self._mailbox)
                if status == "OK":
                    uidvalidity = self._get_uidvalidity(data)

            # Search for UIDs after the cursor
            search_uid = cursor.last_uid + 1
            status, data = client.uid("SEARCH", None, f"UID {search_uid}:*")
            if status != "OK" or not data or not data[0]:
                return messages, MailCursor(
                    last_uid=cursor.last_uid,
                    last_poll_at=time.time(),
                    uidvalidity=uidvalidity or cursor.uidvalidity,
                )

            uid_list = data[0].split()
            for imap_uid in uid_list:
                uid_str = imap_uid.decode("utf-8", errors="ignore") if isinstance(imap_uid, bytes) else str(imap_uid)

                # Determine fetch mode
                fetch_cmd = "(BODY.PEEK[] FLAGS)" if not self._mark_seen else "(BODY[] FLAGS)"

                status, fetched = client.uid("FETCH", imap_uid, fetch_cmd)
                if status != "OK" or not fetched:
                    continue

                raw_bytes = self._extract_message_bytes(fetched)
                if raw_bytes is None:
                    continue

                msg = self._parse_fetched_message(raw_bytes, uid_str)
                messages.append(msg)

            # Build new cursor
            new_uid = max(
                (int(m.uid) for m in messages),
                default=cursor.last_uid,
            )
            new_cursor = MailCursor(
                last_uid=new_uid,
                last_poll_at=time.time(),
                uidvalidity=uidvalidity or cursor.uidvalidity,
            )
        finally:
            try:
                client.logout()
            except Exception:
                pass

        return messages, new_cursor

    def fetch_range(
        self, since: datetime, until: datetime, limit: int = 50
    ) -> list[RawMessage]:
        """Fetch messages within a date range (for summaries).

        Uses IMAP ``SINCE`` / ``BEFORE`` search with ``UID SEARCH``.

        Returns:
            Up to *limit* messages in the range.
        """
        messages: list[RawMessage] = []
        client = self._connect()

        try:
            since_str = _format_imap_date(since)
            until_str = _format_imap_date(until)

            status, data = client.search(
                None, "SINCE", since_str, "BEFORE", until_str
            )
            if status != "OK" or not data or not data[0]:
                return messages

            ids = data[0].split()
            if limit > 0 and len(ids) > limit:
                ids = ids[-limit:]

            for imap_id in ids:
                status, fetched = client.fetch(imap_id, "(BODY.PEEK[] FLAGS)")
                if status != "OK" or not fetched:
                    continue

                uid = self._extract_uid(fetched)
                raw_bytes = self._extract_message_bytes(fetched)
                if raw_bytes is None:
                    continue

                msg = self._parse_fetched_message(raw_bytes, uid)
                messages.append(msg)
        finally:
            try:
                client.logout()
            except Exception:
                pass

        return messages

    def test_connection(self) -> ConnectionResult:
        """Test IMAP connection by logging in and selecting the mailbox.

        Returns:
            ``ConnectionResult`` with success status and folder info.
        """
        try:
            client = self._connect()
            try:
                # Gather folder info
                status, data = client.select(self._mailbox)
                if status == "OK":
                    uidvalidity = self._get_uidvalidity(data)

                    # Get EXISTS count
                    exists = 0
                    for item in data or []:
                        if isinstance(item, bytes):
                            m = re.search(rb"(\d+)\s+EXISTS", item)
                            if m:
                                exists = int(m.group(1))
                                break

                    info_parts = []
                    if uidvalidity is not None:
                        info_parts.append(f"UIDVALIDITY {uidvalidity}")
                    info_parts.append(f"EXISTS {exists}")
                    folder_info = f"{self._mailbox} ({', '.join(info_parts)})"

                    return ConnectionResult(
                        success=True,
                        message="Connected successfully",
                        folder_info=folder_info,
                    )
                return ConnectionResult(
                    success=False,
                    message=f"SELECT failed for {self._mailbox}",
                )
            finally:
                try:
                    client.logout()
                except Exception:
                    pass
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=str(e),
            )

    # ── Internal helpers ─────────────────────────────────────────────────

    def _parse_fetched_message(self, raw_bytes: bytes, uid: str) -> RawMessage:
        """Parse raw IMAP-fetched bytes into a ``RawMessage``.

        This method exists so it can be overridden in tests or subclasses.
        """
        parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)

        subject = decode_header_value(parsed.get("Subject", ""))
        from_ = decode_header_value(parsed.get("From", ""))
        message_id = (parsed.get("Message-ID") or "").strip()
        date_str = parsed.get("Date")

        date = None
        if date_str:
            try:
                from email.utils import parsedate_to_datetime

                date = parsedate_to_datetime(date_str)
            except Exception:
                pass

        text_body = extract_text_body(parsed)

        # Collect key headers
        headers: dict[str, str] = {}
        for hdr in ("Message-ID", "Subject", "From", "To", "Date", "References", "In-Reply-To"):
            val = parsed.get(hdr, "")
            if val:
                headers[hdr] = val

        return RawMessage(
            uid=uid,
            subject=subject,
            from_=from_,
            message_id=message_id or None,
            date=date,
            text_body=text_body,
            headers=headers,
        )
