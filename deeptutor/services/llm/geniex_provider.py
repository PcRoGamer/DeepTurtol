"""
GenieX NPU Local LLM Provider
=============================

Executes local SLMs (e.g. Google Gemma 4 E2B QAT) on the Qualcomm Hexagon NPU via GenieX CLI.
"""

import os
import shutil
import subprocess
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)

GENIEX_CLI_PATH = r"C:\Users\Admin\AppData\Local\GenieX CLI\geniex.exe"

def find_geniex_executable() -> Optional[str]:
    if os.path.exists(GENIEX_CLI_PATH):
        return GENIEX_CLI_PATH
    in_path = shutil.which("geniex")
    if in_path:
        return in_path
    return None

async def complete(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = "local/gemma4-e2b-qat",
    compute: str = "npu",
    max_tokens: int = 1024,
    messages: List[Dict[str, str]] | None = None,
    **kwargs: Any,
) -> str:
    """
    Complete a prompt using GenieX NPU CLI.
    """
    geniex_exe = find_geniex_executable()
    if not geniex_exe:
        raise RuntimeError(f"GenieX executable not found at {GENIEX_CLI_PATH}")

    # Build prompt string from messages if provided
    full_prompt = ""
    if messages:
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                full_prompt += f"\nUser: {content}"
            elif role == "assistant":
                full_prompt += f"\nAssistant: {content}"
        full_prompt += "\nAssistant:"
    else:
        full_prompt = prompt

    model_name = model or "local/gemma4-e2b-qat"
    cmd = [
        geniex_exe,
        "infer", model_name,
        "--compute", compute,
        "-s", system_prompt,
        "-p", full_prompt,
        "--max-tokens", str(max_tokens),
        "--think=false",
        "--skip-update"
    ]

    logger.info(f"Executing GenieX on {compute.upper()} NPU: {model_name}")

    def _run_proc():
        proc = subprocess.run(cmd, capture_output=True, text=False, timeout=120)
        out = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        err = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
        return out, err, proc.returncode

    loop = asyncio.get_event_loop()
    out, err, code = await loop.run_in_executor(None, _run_proc)

    if code != 0:
        logger.error(f"GenieX execution failed with code {code}: {err}")
        raise RuntimeError(f"GenieX execution error: {err or out}")

    # Clean timing line output from GenieX (e.g. — 24.8 tok/s • 99 tok • 0.1 s first token —)
    clean_text = re.sub(r"—\s*[\d\.]+\s*tok/s\s*•\s*\d+\s*tok\s*•\s*[\d\.]+\s*s first token\s*—", "", out)
    # Clean loading spinners
    clean_text = re.sub(r"[🌎🌏🌍]loading model\.\.\.", "", clean_text)
    clean_text = re.sub(r"[🌎🌏🌍]encoding\.\.\.", "", clean_text)
    # Strip ANSI escape codes (terminal control sequences)
    clean_text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", clean_text)
    clean_text = re.sub(r"\x1b\[\?[0-9]*[a-zA-Z]", "", clean_text)
    
    # Remove initial prompt reflection if present
    if full_prompt in clean_text:
        clean_text = clean_text.split(full_prompt)[-1]
        
    return clean_text.strip()

async def complete_stream(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = "local/gemma4-e2b-qat",
    compute: str = "npu",
    max_tokens: int = 1024,
    messages: List[Dict[str, str]] | None = None,
    **kwargs: Any,
) -> AsyncGenerator[str, None]:
    """
    Stream completion from GenieX NPU CLI.
    """
    res = await complete(prompt, system_prompt, model, compute, max_tokens, messages, **kwargs)
    yield res
