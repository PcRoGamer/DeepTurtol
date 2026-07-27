"""LLM Server Manager — lifecycle manager for the LLM HTTP endpoint used by GraphRAG.

GraphRAG (via LiteLLM) needs an OpenAI-compatible HTTP server.  This manager:

1. If the active provider is local (Ollama), ensures Ollama is running.
2. If the active provider is remote (OpenCode Zen, etc.), no local server needed.
3. Exposes the active endpoint URL for downstream consumers (GraphRAG config).
4. Handles graceful shutdown.

Singleton pattern: use :func:`get_llm_server_manager` for a process-wide instance.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
import urllib.request

logger = logging.getLogger(__name__)

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


class LLMServerManager:
    """Manages the lifecycle of local LLM servers used by GraphRAG.

    For remote providers (OpenCode Zen, etc.) no local server is needed —
    the endpoint URL is used directly.  For local providers (Ollama),
    ensures the server is running.
    """

    def __init__(self) -> None:
        self._endpoint_url: str | None = None
        self._backend: str | None = None
        self._lock = threading.Lock()
        self._started = False

    @property
    def endpoint_url(self) -> str | None:
        """The active OpenAI-compatible base URL, or None if not started."""
        return self._endpoint_url

    @property
    def backend(self) -> str | None:
        """Which backend is active: 'ollama', 'remote', or None."""
        return self._backend

    def start(self) -> str | None:
        """Start/ensure the LLM server, return the base URL.

        Returns the URL string on success, or None if no backend could start.
        """
        with self._lock:
            if self._started:
                return self._endpoint_url

            # Determine the active provider type from the model catalog
            provider_type, base_url = self._resolve_active_provider()

            if provider_type == "local":
                # Local provider (Ollama) — ensure it's running
                url = self._start_ollama(base_url)
                if url:
                    self._endpoint_url = url
                    self._backend = "ollama"
                    self._started = True
                    logger.info("LLM server started: Ollama at %s", url)
                    return url
                logger.warning("Ollama could not be started")
                return None
            else:
                # Remote provider (OpenCode Zen, etc.) — no local server needed
                if base_url:
                    self._endpoint_url = base_url
                    self._backend = "remote"
                    self._started = True
                    logger.info("LLM server: using remote endpoint %s", base_url)
                    return base_url
                logger.warning("No LLM endpoint configured")
                return None

    def stop(self) -> None:
        """Shut down the managed server process (if any)."""
        with self._lock:
            self._endpoint_url = None
            self._backend = None
            self._started = False

    # -- Private helpers --

    @staticmethod
    def _resolve_active_provider() -> tuple[str, str | None]:
        """Check the model catalog and return (provider_type, base_url).

        provider_type is "local" (Ollama) or "remote" (OpenCode Zen, etc.).
        """
        try:
            from deeptutor.services.config import resolve_llm_runtime_config
            cfg = resolve_llm_runtime_config()
            binding = getattr(cfg, "binding", None)
            base_url = getattr(cfg, "effective_url", None) or getattr(cfg, "base_url", None)

            if binding in ("ollama",):
                return "local", base_url
            else:
                return "remote", base_url
        except Exception as e:
            logger.warning("Could not resolve LLM provider: %s", e)
            return "remote", None

    def _start_ollama(self, configured_url: str | None = None) -> str | None:
        """Ensure Ollama is running and return its OpenAI-compatible URL."""
        from deeptutor.services.local_slm_launcher import (
            ensure_local_slm_running,
            is_ollama_server_running,
        )

        url = configured_url or f"http://localhost:{OLLAMA_PORT}"

        # Quick check — already running?
        if is_ollama_server_running(url):
            logger.info("Ollama already running at %s", url)
            return f"{url}/v1"

        # Try to auto-start
        result = ensure_local_slm_running(model_name="gemma-4-e2b-it", host_url=url)
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
