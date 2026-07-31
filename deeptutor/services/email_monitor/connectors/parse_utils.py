"""Shared email parsing utilities.

Patterns adapted from ``deeptutor/partners/channels/email.py``.
"""

from __future__ import annotations

import html as html_module
import re
from email import policy
from email.header import decode_header, make_header
from email.message import Message
from email.parser import BytesParser

from deeptutor.services.email_monitor.models import RawMessage


def decode_header_value(value: str | None) -> str:
    """Decode an email header value, handling encoded words.

    Handles ``=?UTF-8?B?...?=`` and ``=?UTF-8?Q?...?=`` encoded headers.
    """
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _get_part_payload(part: Message) -> str:
    """Safely extract string payload from an email part."""
    try:
        payload = part.get_content()
    except Exception:
        payload_bytes = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        payload = payload_bytes.decode(charset, errors="replace")
    if not isinstance(payload, str):
        return ""
    return payload


def extract_text_body(msg: Message) -> str:
    """Best-effort extraction of readable body text from an email message.

    For multipart messages, prefers ``text/plain`` parts over ``text/html``.
    For single-part messages, returns the payload directly (with HTML→text
    conversion if the content type is HTML).
    """
    if msg.is_multipart():
        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            payload = _get_part_payload(part)
            if not payload:
                continue
            if content_type == "text/plain":
                plain_parts.append(payload)
            elif content_type == "text/html":
                html_parts.append(payload)
        if plain_parts:
            return "\n\n".join(plain_parts).strip()
        if html_parts:
            return html_to_text("\n\n".join(html_parts)).strip()
        return ""

    payload = _get_part_payload(msg)
    if not payload:
        return ""
    if msg.get_content_type() == "text/html":
        return html_to_text(payload).strip()
    return payload.strip()


def html_to_text(raw_html: str) -> str:
    """Simple HTML-to-text conversion without external dependencies.

    Replaces ``<br>`` and ``</p>`` with newlines, strips remaining tags,
    and unescapes HTML entities.
    """
    text = re.sub(r"<\s*br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"<\s*/\s*p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html_module.unescape(text)


def parse_raw_message(raw_bytes: bytes, uid: str) -> RawMessage:
    """Parse raw email bytes into a ``RawMessage`` model."""
    parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    subject = decode_header_value(parsed.get("Subject", ""))
    from_ = decode_header_value(parsed.get("From", ""))
    to_raw = decode_header_value(parsed.get("To", ""))
    message_id = (parsed.get("Message-ID") or "").strip()
    date_str = parsed.get("Date")

    # Parse date if present
    date = None
    if date_str:
        try:
            from email.utils import parsedate_to_datetime

            date = parsedate_to_datetime(date_str)
        except Exception:
            pass

    # Parse To field into a list of email addresses
    to_list: list[str] = []
    if to_raw:
        from email.utils import getaddresses

        # Simple split on commas for basic cases
        for addr in to_raw.split(","):
            addr = addr.strip()
            if addr:
                to_list.append(addr)

    text_body = extract_text_body(parsed)

    # Extract HTML body separately for reference
    html_body: str | None = None
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() == "text/html":
                html_body = _get_part_payload(part)
                break
    elif parsed.get_content_type() == "text/html":
        html_body = _get_part_payload(parsed)

    # Collect key headers for fallback dedup
    headers: dict[str, str] = {}
    for hdr in ("Message-ID", "Subject", "From", "To", "Date", "References", "In-Reply-To"):
        val = parsed.get(hdr, "")
        if val:
            headers[hdr] = val

    return RawMessage(
        uid=uid,
        subject=subject,
        from_=from_,
        to=to_list,
        date=date,
        text_body=text_body,
        html_body=html_body,
        message_id=message_id or None,
        headers=headers,
    )
