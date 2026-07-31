"""Tests for the email monitor LLM summarizer parser.

The actual LLM call is not tested (it requires a real LLM). Instead,
we test the ``_parse_summary_response`` and ``_fallback_summary``
utilities and verify that the module-level function can be imported.
"""

from __future__ import annotations

from deeptutor.services.email_monitor.summarizer import (
    _fallback_summary,
    _parse_summary_response,
)


def test_parse_valid_summary_json() -> None:
    response = (
        '{"title": "Email Digest — 2026-07-01", '
        '"themes": ["Assignments", "Meetings"], '
        '"action_items": ["Submit HW1"], '
        '"noise_count": 2, '
        '"overall_summary": "Busy day ahead."}'
    )
    result = _parse_summary_response(response, "2026-07-01")
    assert result["title"] == "Email Digest — 2026-07-01"
    assert result["themes"] == ["Assignments", "Meetings"]
    assert result["action_items"] == ["Submit HW1"]
    assert result["noise_count"] == 2
    assert result["overall_summary"] == "Busy day ahead."


def test_parse_summary_with_markdown_fences() -> None:
    response = """```json
{"title": "Digest - 2026", "themes": ["Exams"], "action_items": [], "noise_count": 1, "overall_summary": "Exam week"}
```"""
    result = _parse_summary_response(response, "2026-07-01")
    assert result["title"] == "Digest - 2026"
    assert result["themes"] == ["Exams"]
    assert result["overall_summary"] == "Exam week"


def test_parse_summary_malformed_json_returns_fallback() -> None:
    response = "not json at all"
    result = _parse_summary_response(response, "2026-07-01")
    assert result["noise_count"] == 0  # fallback with empty messages list
    assert "LLM summarization unavailable" in result["overall_summary"]


def test_parse_summary_empty_response() -> None:
    result = _parse_summary_response("", "2026-07-01")
    assert result["noise_count"] == 0
    assert "LLM summarization unavailable" in result["overall_summary"]


def test_fallback_summary_empty_messages() -> None:
    result = _fallback_summary([], "2026-07-01")
    assert result["title"] == "Email Digest — 2026-07-01"
    assert result["themes"] == []
    assert result["action_items"] == []
    assert result["noise_count"] == 0
    assert result["overall_summary"] == "0 emails received in this period. LLM summarization unavailable."


def test_fallback_summary_with_messages() -> None:
    messages = ["msg1", "msg2", "msg3"]  # any iterable works for len()
    result = _fallback_summary(messages, "2026-07-01")
    assert result["noise_count"] == 3
    assert result["overall_summary"] == "3 emails received in this period. LLM summarization unavailable."


def test_generate_summary_is_async_and_callable() -> None:
    """Smoke test: the generate_summary function exists and is async."""
    from deeptutor.services.email_monitor.summarizer import generate_summary

    import asyncio

    assert asyncio.iscoroutinefunction(generate_summary)


def test_module_has_exports() -> None:
    """Verify expected names are exported from the module."""
    from deeptutor.services.email_monitor import generate_summary

    import asyncio

    assert asyncio.iscoroutinefunction(generate_summary)
