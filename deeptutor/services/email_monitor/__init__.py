"""Email monitor: data models and persistent store for inbox watching."""

from .models import (
    ConnectionResult,
    EmailMonitorSettings,
    LedgerEntry,
    MailCursor,
    RawMessage,
)
from .store import (
    EmailMonitorStore,
    _EmailMonitorStoreProxy,
    email_monitor_store,
    get_email_monitor_store,
)

# Level 1 tools — extract & summarise
from .extractor import extract_from_message
from .summarizer import generate_summary
from .service import EmailMonitorService, email_monitor_service, get_email_monitor_service

__all__ = [
    "ConnectionResult",
    "EmailMonitorSettings",
    "EmailMonitorStore",
    "LedgerEntry",
    "MailCursor",
    "RawMessage",
    "email_monitor_store",
    "get_email_monitor_store",
    # Extractor / summarizer / service
    "extract_from_message",
    "generate_summary",
    "EmailMonitorService",
    "email_monitor_service",
    "get_email_monitor_service",
]
