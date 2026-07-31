"""Graph API connector stub — placeholder for Microsoft Graph OAuth v2.

The `auth_mode` field in ``EmailMonitorSettings`` already accepts ``"graph"``
as a value, and the settings UI will show a "Coming soon" badge when that mode
is selected. This stub exists so the connector-import chain works end-to-end
once the real implementation lands.

To implement:
  1. Register an Azure AD app with the ``Mail.Read`` (and optionally
     ``Mail.ReadWrite``) delegated permission.
  2. Implement OAuth device-code or authorization-code flow.
  3. Replace the methods below with real Microsoft Graph API calls
     (GET /me/messages, /me/messages?$filter=receivedDateTime ge ...).
"""

from __future__ import annotations

from datetime import datetime

from deeptutor.services.email_monitor.connectors.base import EmailConnector
from deeptutor.services.email_monitor.models import ConnectionResult, MailCursor, RawMessage


class GraphConnector(EmailConnector):
    """Placeholder Graph API connector.

    Raises ``NotImplementedError`` on every method.  Swap in the real
    implementation once OAuth registration and token management are wired.
    """

    def __init__(self, settings: object) -> None:
        self._settings = settings

    def list_new_messages(
        self, cursor: MailCursor
    ) -> tuple[list[RawMessage], MailCursor]:
        raise NotImplementedError("Graph connector — not yet implemented")

    def fetch_range(
        self, since: datetime, until: datetime, limit: int = 50
    ) -> list[RawMessage]:
        raise NotImplementedError("Graph connector — not yet implemented")

    def test_connection(self) -> ConnectionResult:
        return ConnectionResult(
            success=False,
            message="Microsoft Graph OAuth is not yet supported. "
            "Use IMAP with an app password instead.",
        )
