from __future__ import annotations

import pytest

try:
    from fastapi import FastAPI
except Exception:
    FastAPI = None

pytestmark = pytest.mark.skipif(FastAPI is None, reason="fastapi not installed")

from deeptutor.api import main as api_main


def test_email_monitor_imports():
    """Verify that the email monitor service can be imported from the lifespan module."""
    from deeptutor.services.email_monitor import get_email_monitor_service

    svc = get_email_monitor_service()
    assert svc is not None
