"""Lifecycle management for the native OpenSPG service hosted in WSL2."""
from __future__ import annotations

import os
import re
import subprocess
import time
from urllib.request import urlopen


def ensure_native_kag_ready(timeout: int = 60) -> str:
    """Start/probe the configured WSL2 OpenSPG endpoint and return its URL."""
    configured = os.getenv("KAG_PROJECT_HOST_ADDR")
    if configured:
        if _healthy(configured):
            return configured.rstrip("/")
        raise RuntimeError(f"Configured OpenSPG endpoint is unhealthy: {configured}")
    if os.name != "nt":
        url = "http://127.0.0.1:8887"
        if not _healthy(url):
            raise RuntimeError("OpenSPG is not healthy at http://127.0.0.1:8887")
        return url
    # Service script is idempotent: it starts MariaDB/Neo4j/OpenSPG only when absent.
    subprocess.run(["wsl.exe", "-d", "Debian", "-u", "root", "--", "bash", "-lc", "/opt/deeptutor/bin/openspg-start"], check=True, timeout=30)
    output = subprocess.check_output(["wsl.exe", "-d", "Debian", "-u", "root", "--", "hostname", "-I"], text=True, timeout=8)
    match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", output)
    if not match:
        raise RuntimeError("Could not resolve the WSL2 address for OpenSPG")
    url = f"http://{match.group(0)}:8887"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _healthy(url):
            os.environ["KAG_PROJECT_HOST_ADDR"] = url
            return url
        time.sleep(1)
    raise RuntimeError(f"OpenSPG did not become healthy within {timeout}s")


def _healthy(url: str) -> bool:
    try:
        with urlopen(f"{url.rstrip('/')}/public/v1/project", timeout=2) as response:  # nosec B310
            return response.status == 200
    except OSError:
        return False
