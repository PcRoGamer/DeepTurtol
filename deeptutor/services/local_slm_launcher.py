import json
import logging
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def find_ollama_executable() -> Optional[Path]:
    """
    Searches for Ollama executable across system PATH and standard Windows installation locations.
    """
    # 1. System PATH
    exe_in_path = shutil.which("ollama")
    if exe_in_path:
        return Path(exe_in_path)

    # 2. Windows LocalAppData & Program Files
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    
    candidate_paths = [
        Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe",
        Path(program_files) / "Ollama" / "ollama.exe",
        Path("C:\\Users\\Admin\\AppData\\Local\\Programs\\Ollama\\ollama.exe"),
    ]

    for path in candidate_paths:
        if path.exists() and path.is_file():
            return path

    return None


def is_ollama_server_running(host_url: str = "http://localhost:11434") -> bool:
    """
    Checks if Ollama server is responding to health probes on port 11434.
    """
    endpoint = f"{host_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "DeepTutor-SLM-Launcher"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_installed_ollama_models(host_url: str = "http://localhost:11434") -> List[str]:
    """
    Retrieves list of installed model tags from local Ollama server.
    """
    endpoint = f"{host_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "DeepTutor-SLM-Launcher"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return [m.get("name", "") for m in data.get("models", [])]
    except Exception as err:
        logger.debug(f"Failed to fetch Ollama installed models: {err}")
    return []


def ensure_local_slm_running(
    model_name: str = "phi4-mini", host_url: str = "http://localhost:11434"
) -> Dict[str, Any]:
    """
    Ensures local Ollama background server is running and provisions target SLM model if missing.
    """
    result: Dict[str, Any] = {
        "server_running": False,
        "server_auto_started": False,
        "executable_found": False,
        "executable_path": None,
        "model_available": False,
        "installed_models": [],
        "message": "",
    }

    exe_path = find_ollama_executable()
    if exe_path:
        result["executable_found"] = True
        result["executable_path"] = str(exe_path)

    # 1. Check if server is already running
    if is_ollama_server_running(host_url):
        result["server_running"] = True
    else:
        logger.info(f"Local Ollama server at {host_url} is offline. Attempting auto-launch...")
        if not exe_path:
            result["message"] = (
                f"Ollama server is offline and executable was not found on system PATH. "
                f"Please install Ollama from https://ollama.com to run local SLMs like {model_name}."
            )
            logger.warning(result["message"])
            return result

        # Spawn background process `ollama serve`
        try:
            subprocess.Popen(
                [str(exe_path), "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            logger.info(f"Spawned background process '{exe_path} serve'")
            result["server_auto_started"] = True

            # Wait up to 5 seconds for server to respond
            for _ in range(10):
                time.sleep(0.5)
                if is_ollama_server_running(host_url):
                    result["server_running"] = True
                    logger.info("[OK] Ollama server auto-start verified online!")
                    break
        except Exception as spawn_err:
            logger.error(f"Failed to auto-spawn Ollama server: {spawn_err}")
            result["message"] = f"Failed to spawn Ollama server: {spawn_err}"
            return result

    # 2. Check if target model is present in installed models list
    if result["server_running"]:
        models = get_installed_ollama_models(host_url)
        result["installed_models"] = models
        clean_target = model_name.lower().split(":")[0]
        result["model_available"] = any(clean_target in m.lower() for m in models)

        if result["model_available"]:
            result["message"] = f"Local SLM server is online and model '{model_name}' is available."
        else:
            result["message"] = (
                f"Local SLM server is online, but model '{model_name}' is not pulled yet. "
                f"Run `ollama pull {model_name}` to download weights for offline execution."
            )
            logger.info(result["message"])

    return result
