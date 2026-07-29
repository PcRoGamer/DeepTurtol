"""Local Qualcomm QNN Whisper STT adapter for Windows on ARM.

The adapter is deliberately opt-in. Set ``DEEPTUTOR_QNN_WHISPER_MODEL_DIR``
for Whisper-base chat transcription and
``DEEPTUTOR_QNN_WHISPER_LARGE_V3_TURBO_MODEL_DIR`` for lecture transcription.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import wave

import numpy as np

from deeptutor.services.voice.base import BaseSTTAdapter, VoiceProviderError
from deeptutor.services.voice.config import STTConfig

_PYTHON_ENV = "DEEPTUTOR_QNN_WHISPER_PYTHON"
_REQUIRED_MODELS = ("HfWhisperEncoder.onnx", "HfWhisperDecoder.onnx")
_MODEL_DIR_ENVS = {
    "base": "DEEPTUTOR_QNN_WHISPER_MODEL_DIR",
    "large-v3-turbo": "DEEPTUTOR_QNN_WHISPER_LARGE_V3_TURBO_MODEL_DIR",
}


def _model_paths(model: str) -> tuple[Path, Path]:
    configured_env = _MODEL_DIR_ENVS.get(model)
    if configured_env is None:
        raise VoiceProviderError(
            f"Unsupported QNN Whisper model {model!r}. Choose one of: {', '.join(_MODEL_DIR_ENVS)}."
        )
    configured_dir = os.environ.get(configured_env, "").strip()
    if not configured_dir:
        raise VoiceProviderError(
            f"QNN Whisper {model} is not configured: set {configured_env} to its cached model directory."
        )
    model_dir = Path(configured_dir).expanduser()
    paths = tuple(model_dir / name for name in _REQUIRED_MODELS)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise VoiceProviderError("QNN Whisper model artifacts are missing: " + ", ".join(missing))
    return paths[0], paths[1]


def _validate_runtime() -> None:
    if platform.system() != "Windows" or platform.machine().lower() not in {"arm64", "aarch64"}:
        raise VoiceProviderError("QNN Whisper requires native Windows ARM64.")
    configured_python = os.environ.get(_PYTHON_ENV)
    if configured_python and Path(configured_python).resolve() != Path(os.sys.executable).resolve():
        raise VoiceProviderError(
            f"{_PYTHON_ENV} must point to the Python interpreter running DeepTutor. "
            "Run DeepTutor from the native QNN environment."
        )
    try:
        import onnxruntime as ort
        from qai_hub_models.utils.onnx.torch_wrapper import _verify_onnxruntime_qnn_installed

        _verify_onnxruntime_qnn_installed()
        if "QNNExecutionProvider" not in ort.get_available_providers():
            raise VoiceProviderError("QNNExecutionProvider is not available in this Python runtime.")
    except VoiceProviderError:
        raise
    except Exception as exc:
        raise VoiceProviderError(f"QNN Whisper runtime validation failed: {exc}") from exc


def _load_audio(path: Path) -> np.ndarray:
    if shutil.which("ffmpeg"):
        command = [
            "ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le",
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-",
        ]
        completed = subprocess.run(command, capture_output=True, check=False)
        if completed.returncode:
            raise VoiceProviderError(f"FFmpeg could not decode audio: {completed.stderr.decode(errors='replace')}")
        return np.frombuffer(completed.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if path.suffix.lower() != ".wav":
        raise VoiceProviderError("FFmpeg is required to decode non-WAV audio for local QNN Whisper.")
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2 or source.getframerate() != 16000:
            raise VoiceProviderError("Without FFmpeg, QNN Whisper accepts only 16 kHz 16-bit PCM WAV audio.")
        channels = source.getnchannels()
        audio = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return audio.reshape(-1, channels).mean(axis=1) if channels > 1 else audio


def _transcribe(audio_path: Path, model: str) -> str:
    _validate_runtime()
    encoder_path, decoder_path = _model_paths(model)
    from qai_hub_models.models._shared.hf_whisper.app import HfWhisperApp
    from qai_hub_models.utils.onnx.torch_wrapper import OnnxModelTorchWrapper

    audio = _load_audio(audio_path)
    app = HfWhisperApp(
        OnnxModelTorchWrapper.OnNPU(encoder_path),
        OnnxModelTorchWrapper.OnNPU(decoder_path),
        f"openai/whisper-{model}",
    )
    chunk_size, overlap = 30 * 16000, 16000
    texts: list[str] = []
    for offset in range(0, len(audio), chunk_size - overlap):
        chunk = audio[offset : offset + chunk_size]
        if len(chunk) < 16000:
            break
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        text = str(app.transcribe(chunk, 16000)).strip()
        if text:
            texts.append(text)
    return " ".join(texts)


class QNNWhisperSTTAdapter(BaseSTTAdapter):
    """Run cached Whisper base or large-v3-turbo artifacts on local Qualcomm HTP."""

    async def transcribe(
        self,
        audio: bytes,
        config: STTConfig,
        *,
        filename: str = "audio.webm",
        content_type: str = "application/octet-stream",
    ) -> str:
        if not audio:
            raise VoiceProviderError("No audio data to transcribe.")
        suffix = Path(filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source:
            source.write(audio)
            path = Path(source.name)
        try:
            return await asyncio.to_thread(_transcribe, path, config.model or "base")
        finally:
            path.unlink(missing_ok=True)


__all__ = ["QNNWhisperSTTAdapter"]
