"""Tests for the email monitor LLM extraction parser.

The actual LLM call is not tested (it requires a real LLM). Instead,
we test the ``_parse_extraction_response`` utility and verify that
the module-level function can be imported.
"""

from __future__ import annotations

from deeptutor.services.email_monitor.extractor import _parse_extraction_response


def test_parse_valid_json() -> None:
    response = (
        '{"is_actionable": true, "summary": "Lab report due", '
        '"items": [{"title": "Submit lab 3", "kind": "assignment", "course": "COMP30027"}]}'
    )
    result = _parse_extraction_response(response)
    assert result["is_actionable"] is True
    assert result["summary"] == "Lab report due"
    assert len(result["items"]) == 1
    assert result["items"][0]["title"] == "Submit lab 3"


def test_parse_json_with_markdown_fences() -> None:
    response = """```json
{"is_actionable": true, "summary": "Exam reminder", "items": []}
```"""
    result = _parse_extraction_response(response)
    assert result["is_actionable"] is True
    assert result["summary"] == "Exam reminder"
    assert result["items"] == []


def test_parse_json_with_backtick_fences_no_lang() -> None:
    response = """```
{"is_actionable": false, "summary": "No action", "items": []}
```"""
    result = _parse_extraction_response(response)
    assert result["is_actionable"] is False
    assert result["summary"] == "No action"


def test_parse_malformed_json_returns_fallback() -> None:
    response = "this is not json at all"
    result = _parse_extraction_response(response)
    assert result["is_actionable"] is False
    assert result["summary"] == ""
    assert result["items"] == []


def test_parse_empty_response_returns_fallback() -> None:
    result = _parse_extraction_response("")
    assert result["is_actionable"] is False
    assert result["summary"] == ""
    assert result["items"] == []


def test_parse_json_array_instead_of_object_returns_fallback() -> None:
    """If the LLM returns a JSON array instead of an object, fall back."""
    response = '["item1", "item2"]'
    result = _parse_extraction_response(response)
    assert result["is_actionable"] is False
    assert result["items"] == []


def test_parse_partial_fields() -> None:
    """Missing optional fields should not cause errors."""
    response = '{"is_actionable": true}'
    result = _parse_extraction_response(response)
    assert result["is_actionable"] is True
    assert result["summary"] == ""
    assert result["items"] == []


def test_parse_non_actionable_keeps_summary() -> None:
    response = '{"is_actionable": false, "summary": "Just an info notice", "items": []}'
    result = _parse_extraction_response(response)
    assert result["is_actionable"] is False
    assert result["summary"] == "Just an info notice"


def test_extract_from_message_is_async_and_callable() -> None:
    """Smoke test: the extract function exists and is async."""
    from deeptutor.services.email_monitor.extractor import extract_from_message

    import asyncio

    assert asyncio.iscoroutinefunction(extract_from_message)


def test_module_has_exports() -> None:
    """Verify expected names are exported from the module."""
    from deeptutor.services.email_monitor import extract_from_message

    import asyncio

    assert asyncio.iscoroutinefunction(extract_from_message)
