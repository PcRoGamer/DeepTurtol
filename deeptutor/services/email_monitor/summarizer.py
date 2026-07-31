"""LLM summarization of recent emails for digest generation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from deeptutor.services.email_monitor.models import RawMessage

logger = logging.getLogger(__name__)

SUMMARIZE_SYSTEM_PROMPT = """You are an AI assistant that summarizes recent university emails for a student.

Given a list of recent emails, produce a concise digest covering:
1. Key themes or topics from the emails
2. Important deadlines or action items (reference items already captured in todos)
3. Items that were informational or noise

Respond with JSON only:
{
  "title": "Email Digest — {date_range}",
  "themes": ["Theme 1", "Theme 2"],
  "action_items": ["Action 1", "Action 2"],
  "noise_count": 3,
  "overall_summary": "2-3 sentence overview of inbox activity"
}"""


async def generate_summary(
    messages: list[RawMessage], date_range_label: str
) -> dict[str, Any]:
    """Generate an LLM digest of a batch of emails.

    Returns a dict with keys: title, themes, action_items, noise_count, overall_summary.
    """
    if not messages:
        return {
            "title": f"Email Digest — {date_range_label}",
            "themes": [],
            "action_items": [],
            "noise_count": 0,
            "overall_summary": "No emails in this period.",
        }

    # Build a compact summary of each email
    email_lines = []
    for m in messages:
        body_preview = (m.text_body or "")[:500].replace("\n", " ")
        email_lines.append(
            f"- From: {m.from_ or '(unknown)'} | Subject: {m.subject or '(no subject)'} | "
            f"Date: {m.date.isoformat() if m.date else '?'}\n  {body_preview}"
        )

    user_prompt = (
        f"Date range: {date_range_label}\n\nEmails ({len(messages)}):\n"
        + "\n".join(email_lines)
    )

    try:
        from deeptutor.services.llm import complete

        response = await complete(
            prompt=user_prompt,
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
        )
        return _parse_summary_response(response, date_range_label)
    except Exception as e:
        logger.warning("LLM summarization failed: %s", e, exc_info=True)
        return _fallback_summary(messages, date_range_label)


def _parse_summary_response(response: str, date_range_label: str) -> dict[str, Any]:
    text = response.strip()
    if text.startswith("```"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_summary([], date_range_label)

    return {
        "title": str(data.get("title", f"Email Digest — {date_range_label}")),
        "themes": data.get("themes", []) if isinstance(data.get("themes"), list) else [],
        "action_items": data.get("action_items", []) if isinstance(data.get("action_items"), list) else [],
        "noise_count": int(data.get("noise_count", 0)),
        "overall_summary": str(data.get("overall_summary", "")),
    }


def _fallback_summary(
    messages: list, date_range_label: str
) -> dict[str, Any]:
    return {
        "title": f"Email Digest — {date_range_label}",
        "themes": [],
        "action_items": [],
        "noise_count": len(messages),
        "overall_summary": f"{len(messages)} emails received in this period. LLM summarization unavailable.",
    }
