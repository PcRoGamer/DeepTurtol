"""Email monitor connectors — IMAP, Graph (stub), fake, and parsing utilities."""

from deeptutor.services.email_monitor.connectors.base import EmailConnector
from deeptutor.services.email_monitor.connectors.fake import FakeConnector
from deeptutor.services.email_monitor.connectors.graph import GraphConnector
from deeptutor.services.email_monitor.connectors.imap import ImapConnector
from deeptutor.services.email_monitor.connectors.parse_utils import (
    decode_header_value,
    extract_text_body,
    html_to_text,
    parse_raw_message,
)

# Microsoft 365 IMAP preset
M365_PRESET: dict = {
    "host": "outlook.office365.com",
    "port": 993,
    "use_ssl": True,
}

__all__ = [
    "EmailConnector",
    "FakeConnector",
    "GraphConnector",
    "ImapConnector",
    "M365_PRESET",
    "decode_header_value",
    "extract_text_body",
    "html_to_text",
    "parse_raw_message",
]
