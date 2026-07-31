"""Email Monitor API Router

Provides endpoints for configuring, testing, polling, and summarising
the email monitor feature.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from deeptutor.services.email_monitor import (
    get_email_monitor_store,
    get_email_monitor_service,
    EmailMonitorSettings,
)
from deeptutor.services.email_monitor.connectors.imap import ImapConnector

router = APIRouter(prefix="/api/v1/email-monitor", tags=["email-monitor"])


# === Request/Response Models ===


class SettingsUpdate(BaseModel):
    """Partial settings update model."""

    enabled: bool | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    imap_use_ssl: bool | None = None
    username: str | None = None
    password: str | None = None
    mailbox: str | None = None
    poll_interval_seconds: int | None = None
    sender_filter: str | None = None
    subject_filter: str | None = None
    mark_seen: bool | None = None
    consent_granted: bool | None = None
    auth_mode: str | None = None
    bootstrap_last_n: int | None = None


class SummarizeRequest(BaseModel):
    """Request model for on-demand summarization."""

    since_days: int = 1
    mailbox: str | None = None


# === API Endpoints ===


@router.get("/settings")
async def get_settings():
    """Get current email monitor configuration (password masked)."""
    try:
        store = get_email_monitor_store()
        settings = store.get_settings()
        masked = store.mask_password(settings)
        return {"success": True, "settings": masked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_settings(data: SettingsUpdate):
    """Update email monitor configuration (partial update)."""
    try:
        store = get_email_monitor_store()
        current = store.get_settings()

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        updated = current.model_copy(update=update_data)

        store.save_settings(updated)
        # Reload cache
        store._settings_cache = updated

        return {"success": True, "settings": store.mask_password(updated)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_connection():
    """Test IMAP connection with current settings."""
    try:
        store = get_email_monitor_store()
        settings = store.get_settings()
        connector = ImapConnector(settings)
        result = await asyncio.to_thread(connector.test_connection)
        return {
            "success": result.success,
            "message": result.message,
            "folder_info": result.folder_info,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "folder_info": None}


@router.post("/poll-now")
async def poll_now():
    """Run a single email poll cycle."""
    try:
        service = get_email_monitor_service()
        result = await service.poll_now()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get current email monitor status."""
    try:
        service = get_email_monitor_service()
        return {"success": True, "status": service.get_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize(data: SummarizeRequest = SummarizeRequest()):
    """Generate an on-demand digest of recent emails."""
    try:
        service = get_email_monitor_service()
        result = await service.summarize(
            since_days=data.since_days, mailbox=data.mailbox
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries")
async def list_summaries():
    """List cached email digests."""
    try:
        store = get_email_monitor_store()
        summaries = store.list_summaries()
        items = []
        for s in summaries:
            data = store.load_summary(s)
            items.append({"id": s, "data": data})
        return {"success": True, "summaries": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/{summary_id}")
async def get_summary(summary_id: str):
    """Get a single cached email digest by ID."""
    try:
        store = get_email_monitor_store()
        data = store.load_summary(summary_id)
        if data is None:
            raise HTTPException(
                status_code=404, detail=f"Summary {summary_id} not found"
            )
        return {"success": True, "summary": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
