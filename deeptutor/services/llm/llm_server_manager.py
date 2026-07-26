"""LLM Server Manager — lifecycle manager for the LLM HTTP endpoint used by GraphRAG.

GraphRAG (via LiteLLM) needs an OpenAI-compatible HTTP server.  This manager:

1. Detects the active LLM provider.
2. If ``geniex_npu``: starts the GenieX HTTP bridge subprocess.
3. If GenieX unavailable: falls back to Ollama via ``ensure_local_slm_running``.
4. Exposes the active endpoint URL for downstream consumers (GraphRAG config).
5. Handles graceful shutdown.

Singleton pattern: use :func:`get_llm_server_manager` for a process-wide instance.
"""

from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default ports
GENIEX_BRIDGE_PORT = int(os.environ.get("GENIEX_BRIDGE_PORT", "18080"))
OLLAMA_PORT = 11434


def _is_server_alive(url: str, timeout: float = 2.0) -> bool:
    """Probe an HTTP endpoint for liveness."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "DeepTutor-LLMServerManager"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _is_geniex_available() -> bool:
    """Check if the GenieX CLI executable exists."""
    from deeptutor.services.llm.geniex_bridge import _find_geniex

    return _find_geniex() is not None


class LLMServerManager:
    """Manages the lifecycle of the LLM HTTP server used by GraphRAG.

    The manager tries GenieX bridge first, then falls back to Ollama.
    Only one backend is active at a time.
    """

    def __init__(self) -> None:
        self._endpoint_url: str | None = None
        self._process: subprocess.Popen | None = None
        self._backend: str | None = None  # "geniex_bridge" or "ollama"
        self._lock = threading.Lock()
        self._started = False

    @property
    def endpoint_url(self) -> str | None:
        """The active OpenAI-compatible base URL, or None if not started."""
        return self._endpoint_url

    @property
    def backend(self) -> str | None:
        """Which backend is active: 'geniex_bridge', 'ollama', or None."""
        return self._backend

    def start(self) -> str | None:
        """Start the LLM server, return the base URL.

        Returns the URL string on success, or None if no backend could start.
        """
        with self._lock:
            if self._started:
                return self._endpoint_url

            # --- Strategy 1: GenieX Bridge ---
            if _is_geniex_available():
                url = self._start_geniex_bridge()
                if url:
                    self._endpoint_url = url
                    self._backend = "geniex_bridge"
                    self._started = True
                    logger.info(
                        "LLM server started: GenieX bridge at %s", url
                    )
                    return url
                logger.warning("GenieX bridge failed to start, trying Ollama...")
            else:
                logger.info("GenieX not available, trying Ollama fallback...")

            # --- Strategy 2: Ollama ---
            url = self._start_ollama()
            if url:
                self._endpoint_url = url
                self._backend = "ollama"
                self._started = True
                logger.info("LLM server started: Ollama at %s", url)
                return url

            logger.warning(
                "No LLM HTTP server could be started. "
                "GraphRAG indexing will fail with a connection error."
            )
            return None

    def stop(self) -> None:
        """Shut down the managed server process."""
        with self._lock:
            if self._process and self._process.poll() is None:
                logger.info(
                    "Shutting down %s LLM server (pid=%s)",
                    self._backend,
                    self._process.pid,
                )
                try:
                    self._process.terminate()
                    self._process.wait(timeout=5)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                self._process = None
            self._endpoint_url = None
            self._backend = None
            self._started = False

    # -- Private helpers --

    def _start_geniex_bridge(self) -> str | None:
        """Launch the GenieX bridge subprocess and wait for /health."""
        from deeptutor.services.llm.geniex_bridge import (
            _find_geniex,
            GENIEX_CLI_PATH,
        )

        geniex = _find_geniex()
        if not geniex:
            return None

        port = GENIEX_BRIDGE_PORT
        url = f"http://127.0.0.1:{port}"

        # If already running (e.g. from a previous startup), just verify
        if _is_server_alive(f"{url}/health"):
            logger.info("GenieX bridge already running at %s", url)
            # Return with /v1 suffix for OpenAI SDK compatibility
            return f"{url}/v1"

        # Resolve the bridge module path
        bridge_module = (
            Path(__file__).resolve().parent / "geniex_bridge.py"
        )

        try:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(bridge_module),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "GENIEX_BRIDGE_PORT": str(port)},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._process = proc
        except Exception as exc:
            logger.error("Failed to start GenieX bridge: %s", exc)
            return None

        # Wait up to 10 seconds for the bridge to become healthy
        health_url = f"{url}/health"
        for _ in range(20):
            time.sleep(0.5)
            if _is_server_alive(health_url):
                # Return with /v1 suffix for OpenAI SDK compatibility
                return f"{url}/v1"
            if proc.poll() is not None:
                logger.error(
                    "GenieX bridge process exited early (code=%s)", proc.returncode
                )
                self._process = None
                return None

        logger.error("GenieX bridge did not become healthy within 10s")
        self._process.terminate()
        self._process = None
        return None

    def _start_ollama(self) -> str | None:
        """Ensure Ollama is running and return its OpenAI-compatible URL."""
        from deeptutor.services.local_slm_launcher import (
            ensure_local_slm_running,
            is_ollama_server_running,
        )

        url = f"http://localhost:{OLLAMA_PORT}"

        # Quick check — already running?
        if is_ollama_server_running(url):
            logger.info("Ollama already running at %s", url)
            return f"{url}/v1"

        # Try to auto-start
        result = ensure_local_slm_running(model_name="phi4-mini", host_url=url)
        if result.get("server_running"):
            return f"{url}/v1"

        logger.warning("Ollama could not be started: %s", result.get("message"))
        return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager_instance: LLMServerManager | None = None
_manager_lock = threading.Lock()


def get_llm_server_manager() -> LLMServerManager:
    """Return the process-wide LLMServerManager singleton."""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = LLMServerManager()
                atexit.register(_manager_instance.stop)
    return _manager_instance
