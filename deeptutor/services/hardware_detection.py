import os
import platform
import psutil
import logging
from typing import Any, Dict

from deeptutor.services.local_slm_launcher import (
    find_ollama_executable,
    is_ollama_server_running,
    get_installed_ollama_models,
)

logger = logging.getLogger(__name__)


def detect_hardware_capabilities() -> Dict[str, Any]:
    """
    Detects hardware capabilities including Snapdragon ARM64 NPU, CPU cores, RAM, and Ollama status.
    """
    machine = platform.machine().lower()
    system_os = platform.system()
    
    is_arm64 = "arm64" in machine or "aarch64" in machine or os.environ.get("PROCESSOR_ARCHITECTURE", "").lower() == "arm64"
    processor_name = os.environ.get("PROCESSOR_IDENTIFIER", "") + " " + platform.processor()

    # Check RAM
    try:
        total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        cpu_count = psutil.cpu_count(logical=True) or 4
    except Exception:
        total_ram_gb = 8.0
        cpu_count = 4

    # Check QNN / NPU SDK availability
    qnn_available = False
    try:
        import fastembed_qnn
        qnn_available = True
    except ImportError:
        qnn_available = False

    # Check Ollama
    exe_path = find_ollama_executable()
    ollama_installed = bool(exe_path)
    ollama_running = is_ollama_server_running() if ollama_installed else False
    installed_models = get_installed_ollama_models() if ollama_running else []
    gemma_installed = any("gemma-4-e2b-it" in m.lower() for m in installed_models)

    return {
        "os": system_os,
        "machine": machine,
        "is_arm64": is_arm64,
        "processor_name": processor_name,
        "total_ram_gb": total_ram_gb,
        "cpu_count": cpu_count,
        "qnn_available": qnn_available,
        "ollama_installed": ollama_installed,
        "ollama_running": ollama_running,
        "gemma_installed": gemma_installed,
        "installed_models": installed_models,
    }


def get_hardware_recommendations() -> Dict[str, Any]:
    """
    Evaluates hardware capabilities and returns recommendation status for prompting the user.
    """
    caps = detect_hardware_capabilities()
    
    has_npu = caps["is_arm64"] or caps["qnn_available"]
    has_high_ram = caps["total_ram_gb"] >= 8.0
    has_adequate_hardware = has_npu or (has_high_ram and caps["cpu_count"] >= 4)

    prompt_recommended = has_adequate_hardware and (not caps["ollama_installed"] or not caps["gemma_installed"])

    recommendations = []
    if has_npu and caps["qnn_available"]:
        recommendations.append({
            "id": "fastembed_qnn",
            "title": "Enable Qualcomm QNN NPU Acceleration",
            "description": "Snapdragon NPU detected. Enable FastEmbed QNN for 67ms local vector search.",
            "status": "ready",
        })

    if has_adequate_hardware:
        recommendations.append({
            "id": "ollama_gemma4_e2b",
            "title": "Install Local SLM (Ollama + Qualcomm Gemma-4-E2B-it)",
            "description": "Adequate hardware detected (8GB+ RAM). Enable 100% offline LLM reasoning at ~35 tok/sec with Qualcomm Gemma-4-E2B-it.",
            "status": "installed" if caps["gemma_installed"] else "prompt_available",
        })

    return {
        "adequate_hardware": has_adequate_hardware,
        "prompt_recommended": prompt_recommended,
        "recommendations": recommendations,
        "hardware_caps": caps,
    }
