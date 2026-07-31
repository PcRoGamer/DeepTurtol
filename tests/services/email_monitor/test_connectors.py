"""Tests for email monitor connectors — fake connector and parsing utilities.

All tests use ``FakeConnector`` or parse utilities — no real IMAP connections.
"""

from __future__ import annotations

import email
import time
from datetime import datetime, timezone
from email import policy
from email.header import make_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import BytesParser

from deeptutor.services.email_monitor.connectors import (
    FakeConnector,
    decode_header_value,
    extract_text_body,
    html_to_text,
    parse_raw_message,
)
from deeptutor.services.email_monitor.models import ConnectionResult, MailCursor, RawMessage


# ── FakeConnector tests ──────────────────────────────────────────────────


def test_fake_list_new_messages_returns_new_only() -> None:
    connector = FakeConnector()
    connector.add_message(RawMessage(uid="1", subject="First", from_="a@b.com", text_body="A"))
    connector.add_message(RawMessage(uid="2", subject="Second", from_="a@b.com", text_body="B"))
    connector.add_message(RawMessage(uid="3", subject="Third", from_="a@b.com", text_body="C"))

    cursor = MailCursor(last_uid=1, last_poll_at=time.time())
    msgs, new_cursor = connector.list_new_messages(cursor)

    assert len(msgs) == 2
    assert msgs[0].uid == "2"
    assert msgs[1].uid == "3"
    assert new_cursor.last_uid == 3
    assert new_cursor.last_poll_at > 0


def test_fake_list_new_messages_empty_when_no_new() -> None:
    connector = FakeConnector()
    connector.add_message(RawMessage(uid="1", subject="Only", from_="a@b.com", text_body="X"))

    cursor = MailCursor(last_uid=1, last_poll_at=time.time())
    msgs, new_cursor = connector.list_new_messages(cursor)

    assert len(msgs) == 0
    assert new_cursor.last_uid == 1  # unchanged


def test_fake_list_new_messages_empty_when_no_messages() -> None:
    connector = FakeConnector()

    cursor = MailCursor(last_uid=0, last_poll_at=0.0)
    msgs, new_cursor = connector.list_new_messages(cursor)

    assert len(msgs) == 0
    assert new_cursor.last_uid == 0


def test_fake_fetch_range_date_filtering() -> None:
    connector = FakeConnector()
    dt1 = datetime(2025, 6, 1, tzinfo=timezone.utc)
    dt2 = datetime(2025, 6, 15, tzinfo=timezone.utc)
    dt3 = datetime(2025, 7, 1, tzinfo=timezone.utc)

    connector.add_message(RawMessage(uid="1", subject="Jun 1", from_="a@b.com", text_body="", date=dt1))
    connector.add_message(RawMessage(uid="2", subject="Jun 15", from_="a@b.com", text_body="", date=dt2))
    connector.add_message(RawMessage(uid="3", subject="Jul 1", from_="a@b.com", text_body="", date=dt3))

    since = datetime(2025, 6, 1, tzinfo=timezone.utc)
    until = datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    msgs = connector.fetch_range(since, until)

    assert len(msgs) == 2
    assert {m.uid for m in msgs} == {"1", "2"}


def test_fake_fetch_range_empty_when_no_match() -> None:
    connector = FakeConnector()
    dt = datetime(2025, 6, 15, tzinfo=timezone.utc)
    connector.add_message(RawMessage(uid="1", subject="Jun", from_="a@b.com", text_body="", date=dt))

    since = datetime(2025, 7, 1, tzinfo=timezone.utc)
    until = datetime(2025, 7, 31, tzinfo=timezone.utc)
    msgs = connector.fetch_range(since, until)

    assert len(msgs) == 0


def test_fake_fetch_range_respects_limit() -> None:
    connector = FakeConnector()
    dt = datetime(2025, 6, 15, tzinfo=timezone.utc)
    for i in range(10):
        connector.add_message(RawMessage(uid=str(i + 1), subject=f"Msg {i}", from_="a@b.com", text_body="", date=dt))

    since = datetime(2025, 1, 1, tzinfo=timezone.utc)
    until = datetime(2025, 12, 31, tzinfo=timezone.utc)
    msgs = connector.fetch_range(since, until, limit=3)

    assert len(msgs) == 3


def test_fake_list_new_messages_excludes_messages_without_date() -> None:
    """fetch_range should only return messages with a date set."""
    connector = FakeConnector()
    connector.add_message(RawMessage(uid="1", subject="No date", from_="a@b.com", text_body=""))
    connector.add_message(
        RawMessage(
            uid="2",
            subject="With date",
            from_="a@b.com",
            text_body="",
            date=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )
    )

    since = datetime(2025, 1, 1, tzinfo=timezone.utc)
    until = datetime(2025, 12, 31, tzinfo=timezone.utc)
    msgs = connector.fetch_range(since, until)

    assert len(msgs) == 1
    assert msgs[0].uid == "2"


def test_fake_test_connection_success() -> None:
    connector = FakeConnector()
    result = connector.test_connection()

    assert result.success is True
    assert "Fake INBOX" in (result.folder_info or "")


def test_fake_test_connection_failure() -> None:
    connector = FakeConnector()
    connector.should_fail = True
    connector.fail_message = "Connection refused"

    result = connector.test_connection()

    assert result.success is False
    assert result.message == "Connection refused"


def test_fake_list_new_messages_error_propagation() -> None:
    connector = FakeConnector()
    connector.should_fail = True
    connector.fail_message = "Network timeout"

    import pytest

    with pytest.raises(ConnectionError, match="Network timeout"):
        connector.list_new_messages(MailCursor())


def test_fake_fetch_range_error_propagation() -> None:
    connector = FakeConnector()
    connector.should_fail = True
    connector.fail_message = "IMAP server offline"

    import pytest

    with pytest.raises(ConnectionError, match="IMAP server offline"):
        connector.fetch_range(
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 12, 31, tzinfo=timezone.utc),
        )


def test_fake_add_message_idempotent() -> None:
    """Adding the same message twice should make it appear twice."""
    connector = FakeConnector()
    msg = RawMessage(uid="1", subject="Dup", from_="a@b.com", text_body="X")
    connector.add_message(msg)
    connector.add_message(msg)

    msgs, _ = connector.list_new_messages(MailCursor())
    assert len(msgs) == 2


# ── Parse utility tests ─────────────────────────────────────────────────


def test_decode_header_value_plain() -> None:
    result = decode_header_value("Hello World")
    assert result == "Hello World"


def test_decode_header_value_encoded_b64() -> None:
    """Test decoding a Base64-encoded UTF-8 header."""
    result = decode_header_value("=?UTF-8?B?w6l0w6k=?=")
    assert result == "été"


def test_decode_header_value_encoded_qp() -> None:
    """Test decoding a QP-encoded header."""
    result = decode_header_value("=?UTF-8?Q?Stra=C3=9Fe?=")
    assert result == "Straße"


def test_decode_header_value_mixed() -> None:
    """Test decoding a mixed plain + encoded header."""
    result = decode_header_value("Re: =?UTF-8?B?w6l0w6k=?=")
    assert result == "Re: été"


def test_decode_header_value_none() -> None:
    result = decode_header_value(None)
    assert result == ""


def test_decode_header_value_empty() -> None:
    result = decode_header_value("")
    assert result == ""


def test_extract_text_body_plain() -> None:
    """Single-part plain text message."""
    msg = email.message_from_string(
        "Subject: Test\n\nHello World",
        policy=policy.default,
    )
    result = extract_text_body(msg)
    assert result == "Hello World"


def test_extract_text_body_multipart_alternative() -> None:
    """Multipart/alternative with plain and HTML — should prefer plain."""
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText("Hello plain", "plain", "utf-8"))
    msg.attach(MIMEText("<p>Hello HTML</p>", "html", "utf-8"))

    result = extract_text_body(msg)
    assert result == "Hello plain"


def test_extract_text_body_multipart_html_only() -> None:
    """Multipart/alternative with only HTML — should fall back to HTML."""
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText("<p>Hello HTML</p>", "html", "utf-8"))

    result = extract_text_body(msg)
    # HTML → text conversion strips tags
    assert "Hello HTML" in result


def test_extract_text_body_empty() -> None:
    """Empty message body should return empty string."""
    msg = email.message.Message()
    msg["Subject"] = "Empty"
    result = extract_text_body(msg)
    assert result == ""


def test_html_to_text_br_newlines() -> None:
    html = "Line1<br>Line2<br/>Line3"
    result = html_to_text(html)
    assert "Line1\nLine2\nLine3" in result


def test_html_to_text_p_newlines() -> None:
    html = "<p>Para1</p><p>Para2</p>"
    result = html_to_text(html)
    assert "Para1\nPara2" in result


def test_html_to_text_tag_stripping() -> None:
    html = "<div><b>Bold</b> and <i>italic</i></div>"
    result = html_to_text(html)
    assert result == "Bold and italic"


def test_html_to_text_entity_unescape() -> None:
    html = "Hello &amp; goodbye &lt;3"
    result = html_to_text(html)
    assert result == "Hello & goodbye <3"


def test_html_to_text_empty() -> None:
    assert html_to_text("") == ""


def test_html_to_text_no_html() -> None:
    assert html_to_text("Just text") == "Just text"


def test_parse_raw_message_simple() -> None:
    """Parse a crafted raw email into RawMessage."""
    raw = (
        b"From: sender@example.com\r\n"
        b"To: recipient@example.com\r\n"
        b"Subject: Test Subject\r\n"
        b"Message-ID: <abc123@mail>\r\n"
        b"Date: Mon, 15 Jun 2025 10:30:00 +0000\r\n"
        b"\r\n"
        b"Hello, this is a test."
    )
    msg = parse_raw_message(raw, uid="42")

    assert msg.uid == "42"
    assert msg.subject == "Test Subject"
    assert msg.from_ == "sender@example.com"
    assert msg.text_body == "Hello, this is a test."
    assert msg.message_id == "<abc123@mail>"
    assert msg.date is not None
    assert msg.date.year == 2025
    assert msg.date.month == 6
    assert msg.date.day == 15


def test_parse_raw_message_multipart() -> None:
    """Parse a multipart email preferring text/plain."""
    # Build a multipart message manually
    container = MIMEMultipart("alternative")
    container["From"] = "alice@example.com"
    container["To"] = "bob@example.com"
    container["Subject"] = "=?UTF-8?B?w6l0w6k=?="  # "été"
    container["Message-ID"] = "<multi@test>"

    container.attach(MIMEText("Plain body", "plain", "utf-8"))
    container.attach(MIMEText("<p>HTML body</p>", "html", "utf-8"))

    raw_bytes = container.as_bytes()

    msg = parse_raw_message(raw_bytes, uid="100")

    assert msg.uid == "100"
    assert msg.subject == "été"
    assert msg.from_ == "alice@example.com"
    assert msg.text_body == "Plain body"
    assert msg.message_id == "<multi@test>"


def test_parse_raw_message_no_date() -> None:
    """Parse a message without a Date header."""
    raw = (
        b"From: no@date.com\r\n"
        b"Subject: No Date\r\n"
        b"\r\n"
        b"Body text"
    )
    msg = parse_raw_message(raw, uid="0")

    assert msg.uid == "0"
    assert msg.date is None
    assert msg.text_body == "Body text"


def test_parse_raw_message_populates_headers() -> None:
    """Key headers should be captured in the headers dict."""
    raw = (
        b"From: a@b.com\r\n"
        b"To: c@d.com\r\n"
        b"Subject: Test\r\n"
        b"Message-ID: <hdr-test>\r\n"
        b"References: <ref@prev>\r\n"
        b"Date: Tue, 1 Jan 2025 00:00:00 +0000\r\n"
        b"\r\n"
        b"Body"
    )
    msg = parse_raw_message(raw, uid="7")

    assert msg.headers.get("Message-ID") == "<hdr-test>"
    assert msg.headers.get("Subject") == "Test"
    assert msg.headers.get("From") == "a@b.com"
    assert msg.headers.get("References") == "<ref@prev>"


def test_parse_raw_message_encoded_headers() -> None:
    """Subject and From headers with encoded words should be decoded."""
    raw = (
        b"From: =?UTF-8?B?w6l0w6k=?= <user@test.com>\r\n"
        b"Subject: =?UTF-8?Q?H=C3=B6lle?=\r\n"
        b"\r\n"
        b"Body"
    )
    msg = parse_raw_message(raw, uid="5")

    assert "été" in msg.from_
    assert "Hölle" in msg.subject


# ── ImapConnector instantiation tests ────────────────────────────────────
# We only test that the class exists and can be instantiated.
# Real IMAP tests would require network access or mocking.


def test_imap_connector_can_be_instantiated() -> None:
    from deeptutor.services.email_monitor.connectors.imap import ImapConnector
    from deeptutor.services.email_monitor.models import EmailMonitorSettings

    settings = EmailMonitorSettings(
        username="test@example.com",
        password="secret",
    )
    connector = ImapConnector(settings)

    assert connector is not None
    assert connector._host == "outlook.office365.com"
    assert connector._username == "test@example.com"


def test_imap_connector_defaults() -> None:
    from deeptutor.services.email_monitor.connectors.imap import ImapConnector
    from deeptutor.services.email_monitor.models import EmailMonitorSettings

    settings = EmailMonitorSettings()
    connector = ImapConnector(settings)

    assert connector._host == "outlook.office365.com"
    assert connector._port == 993
    assert connector._use_ssl is True
    assert connector._username == ""
    assert connector._mailbox == "INBOX"
    assert connector._mark_seen is False
