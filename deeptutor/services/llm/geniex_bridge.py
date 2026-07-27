"""GenieX HTTP Bridge — wraps the GenieX CLI into an OpenAI-compatible HTTP API.

GraphRAG's indexing pipeline uses LiteLLM internally, which needs an
OpenAI-compatible HTTP endpoint.  GenieX is a CLI tool (``geniex.exe infer``),
so this bridge runs as a lightweight Starlette server that translates between
the two interfaces.

Usage (standalone)::

    python -m deeptutor.services.llm.geniex_bridge   # starts on :18080

Or launched automatically by :class:`LLMServerManager`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NPU throttling — prevent firmware crash under sustained load
# ---------------------------------------------------------------------------

# Only 1 GenieX call at a time (serialized).  The NPU firmware crashes
# (FF-A library error → watchdog → forced reboot) when hit with concurrent
# or rapid-fire requests.
_NPU_SEMAPHORE = asyncio.Semaphore(1)

# Base cooldown between consecutive NPU calls (seconds).  Gives the Hexagon
# firmware time to recover.  Override with GENIEX_COOLDOWN_SECS env var.
_NPU_BASE_COOLDOWN = float(os.environ.get("GENIEX_COOLDOWN_SECS", "3"))

# Current cooldown (adaptive — increases after failures, resets on success).
_npu_cooldown = _NPU_BASE_COOLDOWN

# Consecutive failure counter — triggers fallback and backoff.
_consecutive_failures = 0

# After this many consecutive NPU failures, fall back to CPU compute.
_MAX_NPU_FAILURES = 3

# Timestamp of the last completed NPU call (for cooldown tracking).
_last_npu_call: float = 0.0

# Track whether we're currently in CPU fallback mode.
_cpu_fallback = False

# ---------------------------------------------------------------------------
# GenieX CLI helpers (reuses logic from geniex_provider.py)
# ---------------------------------------------------------------------------

GENIEX_CLI_PATH = r"C:\Users\Admin\AppData\Local\GenieX CLI\geniex.exe"

# ANSI escape codes + GenieX timing/spinner lines
_RE_TIMING = re.compile(
    r"—\s*[\d.]+\s*tok/s\s*•\s*\d+\s*tok\s*•\s*[\d.]+\s*s first token\s*—"
)
_RE_SPINNER = re.compile(r"[🌎🌏🌍]loading model\.\.\.|[🌎🌏🌍]encoding\.\.\.")
_RE_ANSI_1 = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_RE_ANSI_2 = re.compile(r"\x1b\[\?[0-9]*[a-zA-Z]")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escapes and GenieX noise from raw CLI output."""
    text = _RE_TIMING.sub("", text)
    text = _RE_SPINNER.sub("", text)
    text = _RE_ANSI_1.sub("", text)
    text = _RE_ANSI_2.sub("", text)
    return text.strip()


def _find_geniex() -> str | None:
    """Locate the GenieX executable."""
    import shutil

    if os.path.exists(GENIEX_CLI_PATH):
        return GENIEX_CLI_PATH
    in_path = shutil.which("geniex")
    if in_path:
        return in_path
    return None


async def _call_geniex(
    *,
    model: str,
    system: str,
    prompt: str,
    max_tokens: int = 1024,
    compute: str = "npu",
) -> str:
    """Run ``geniex.exe infer`` and return the cleaned text.

    Serialized via :data:`_NPU_SEMAPHORE` and throttled by
    :data:`_NPU_COOLDOWN` to prevent Qualcomm NPU firmware crashes under
    sustained load.
    """
    global _last_npu_call
    geniex = _find_geniex()
    if not geniex:
        raise RuntimeError("GenieX executable not found")

    # Wait for the semaphore (only 1 NPU call at a time)
    async with _NPU_SEMAPHORE:
        # Enforce cooldown between consecutive calls
        now = asyncio.get_event_loop().time()
        elapsed = now - _last_npu_call
        if elapsed < _NPU_COOLDOWN and _last_npu_call > 0:
            wait = _NPU_COOLDOWN - elapsed
            logger.debug("NPU cooldown: waiting %.1fs", wait)
            await asyncio.sleep(wait)

        cmd = [
            geniex,
            "infer",
            model,
            "--compute", compute,
            "-s", system,
            "-p", prompt,
            "--max-tokens", str(max_tokens),
            "--think=false",
            "--skip-update",
        ]

        def _run() -> tuple[str, str, int]:
            proc = subprocess.run(
                cmd, capture_output=True, text=False, timeout=300,
            )
            out = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
            err = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
            return out, err, proc.returncode

        loop = asyncio.get_running_loop()
        out, err, code = await loop.run_in_executor(None, _run)

        # Record timestamp after call completes (for cooldown)
        _last_npu_call = asyncio.get_event_loop().time()

        if code != 0:
            raise RuntimeError(f"GenieX exited {code}: {err or out}")

        return _strip_ansi(out)


# ---------------------------------------------------------------------------
# Starlette ASGI application
# ---------------------------------------------------------------------------

def _extract_messages(body: dict[str, Any]) -> tuple[str, str]:
    """Pull system prompt and user prompt from OpenAI-format messages."""
    system = "You are a helpful assistant."
    user = ""
    for m in body.get("messages", []):
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "system":
            system = content
        elif role == "user":
            # Concatenate multiple user messages
            user = f"{user}\n{content}".strip() if user else content
    return system, user


async def _handle_chat(request: Any) -> Any:
    """POST /v1/chat/completions — OpenAI-compatible chat endpoint."""
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    req: Request = request
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    model = body.get("model", "local/gemma4-e2b-qat")
    max_tokens = body.get("max_tokens", 1024)
    system, user = _extract_messages(body)

    if not user:
        return JSONResponse(
            {"error": "No user message in request"}, status_code=400
        )

    try:
        text = await _call_geniex(
            model=model,
            system=system,
            prompt=user,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        logger.error("GenieX bridge error: %s", exc)
        return JSONResponse(
            {"error": str(exc)}, status_code=502
        )

    # OpenAI-compatible response
    response_body = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(asyncio.get_event_loop().time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    return JSONResponse(response_body)


async def _handle_health(request: Any) -> Any:
    """GET /health — simple liveness probe."""
    from starlette.responses import JSONResponse

    geniex = _find_geniex()
    return JSONResponse({
        "status": "ok",
        "geniex_available": geniex is not None,
        "geniex_path": geniex,
    })


def create_app() -> Any:
    """Build the Starlette ASGI application."""
    from starlette.applications import Starlette
    from starlette.routing import Route

    routes = [
        # Both paths: LiteLLM's OpenAI SDK sends to {base_url}/chat/completions
        # while some clients use the /v1 prefix explicitly.
        Route("/chat/completions", _handle_chat, methods=["POST"]),
        Route("/v1/chat/completions", _handle_chat, methods=["POST"]),
        Route("/health", _handle_health, methods=["GET"]),
    ]
    return Starlette(routes=routes)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the bridge server as a standalone process."""
    import uvicorn

    port = int(os.environ.get("GENIEX_BRIDGE_PORT", "18080"))
    host = os.environ.get("GENIEX_BRIDGE_HOST", "127.0.0.1")

    logging.basicConfig(level=logging.INFO)
    logger.info("Starting GenieX HTTP Bridge on %s:%d", host, port)

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
