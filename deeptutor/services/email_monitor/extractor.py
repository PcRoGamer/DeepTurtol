"""LLM extraction of actionable items from university emails."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from deeptutor.services.email_monitor.models import RawMessage

logger = logging.getLogger(__name__)

# Schema description to embed in the system prompt
EXTRACTION_SYSTEM_PROMPT = """You are an AI assistant that extracts actionable academic items from university emails.

Given an email, determine if it contains any actionable items (assignments, exams, meetings, admin tasks, or other to-dos with due dates).

Respond with JSON only — no markdown, no explanation, no code fences:

{
  "is_actionable": true,
  "summary": "One-line summary of what this email is about",
  "items": [
    {
      "title": "Submit lab report 3",
      "due_at": "2026-08-15T23:59:00",
      "due_at_confidence": "high",
      "kind": "assignment",
      "course": "COMP30027",
      "priority": "normal",
      "notes": "Optional short note about the item"
    }
  ]
}

Rules:
- is_actionable: true only if there are concrete tasks or deadlines.
- Items may be empty if the email contains no actionable items.
- due_at: ISO 8601 datetime or null if no deadline found.
- due_at_confidence: "high" if explicitly stated, "medium" if implied, "low" if guessed, null if no due date.
- kind: one of "assignment", "exam", "meeting", "admin", "other".
- priority: "high", "normal", or "low".
- course: the course code if discernible, otherwise null.
- Never fabricate due dates. If unsure, set due_at to null and due_at_confidence to null."""


async def extract_from_message(message: RawMessage) -> dict[str, Any]:
    """Use the configured LLM to extract actionable items from a single email.

    Returns a dict with keys: is_actionable, summary, items (list).
    Falls back to non-actionable on any error.
    """
    # Build user prompt from the email content
    subject = message.subject or "(no subject)"
    from_str = message.from_ or "(unknown sender)"
    date_str = message.date.isoformat() if message.date else "(unknown date)"
    body = (message.text_body or "")[:8000]  # truncate to ~8k chars

    user_prompt = f"""From: {from_str}
Subject: {subject}
Date: {date_str}

--- Body ---
{body}"""

    try:
        from deeptutor.services.llm import complete

        response = await complete(
            prompt=user_prompt,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
        )
        return _parse_extraction_response(response)
    except Exception as e:
        logger.warning(
            "LLM extraction failed for message %s: %s", message.uid, e, exc_info=True
        )
        return {"is_actionable": False, "summary": "", "items": []}


def _parse_extraction_response(response: str) -> dict[str, Any]:
    """Parse the LLM JSON response, with safety fallback."""
    # Strip any markdown fences if the LLM ignores instructions
    text = response.strip()
    if text.startswith("```"):
        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse extraction JSON, falling back to non-actionable"
        )
        return {"is_actionable": False, "summary": "", "items": []}

    if not isinstance(data, dict):
        return {"is_actionable": False, "summary": "", "items": []}

    return {
        "is_actionable": bool(data.get("is_actionable", False)),
        "summary": str(data.get("summary", "")),
        "items": data.get("items", []) if isinstance(data.get("items"), list) else [],
    }
