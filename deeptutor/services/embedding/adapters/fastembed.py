"""
FastEmbed Embedding Adapter
===========================

Native local embedding adapter using FastEmbed with ONNX Runtime.
Supports QNNExecutionProvider for Qualcomm NPU hardware acceleration
with graceful fallback to CUDAExecutionProvider / CPUExecutionProvider.
Default model: Qwen/Qwen3-Embedding-0.6B
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base import BaseEmbeddingAdapter, EmbeddingRequest, EmbeddingResponse

logger = logging.getLogger(__name__)

# Cache loaded FastEmbed model instances to avoid redundant ONNX session loading
_FASTEMBED_MODEL_CACHE: Dict[str, Any] = {}


class FastEmbedAdapter(BaseEmbeddingAdapter):
    """
    FastEmbed Adapter using ONNX Runtime.
    Optimized for local low-latency embedding generation on NPU, GPU, or CPU.
    """

    MODELS_INFO = {
        "Qwen/Qwen3-Embedding-0.6B": 1024,
        "Qwen/Qwen3-Embedding-4B": 2560,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "nomic-ai/nomic-embed-text-v1.5": 768,
    }

    DEFAULT_MODEL = "Qwen/Qwen3-Embedding-0.6B"
    DEFAULT_PROVIDERS = [
        "QNNExecutionProvider",
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]

    def _get_or_create_model(self, model_name: str) -> Any:
        global _FASTEMBED_MODEL_CACHE
        cache_key = model_name
        if cache_key in _FASTEMBED_MODEL_CACHE:
            return _FASTEMBED_MODEL_CACHE[cache_key]

        try:
            from fastembed import TextEmbedding
        except ImportError as err:
            raise ImportError(
                "fastembed library is required for FastEmbedAdapter. "
                "Install it with `pip install fastembed`."
            ) from err

        logger.info(
            f"Initializing FastEmbed TextEmbedding model '{model_name}' "
            f"with providers={self.DEFAULT_PROVIDERS}"
        )
        try:
            model = TextEmbedding(
                model_name=model_name,
                providers=self.DEFAULT_PROVIDERS,
            )
        except Exception as exc:
            logger.warning(
                f"Failed to initialize FastEmbed with providers {self.DEFAULT_PROVIDERS}: {exc}. "
                "Falling back to default TextEmbedding initialization."
            )
            model = TextEmbedding(model_name=model_name)

        _FASTEMBED_MODEL_CACHE[cache_key] = model
        return model

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if request.contents:
            raise ValueError(
                "FastEmbed embedding adapter does not support multimodal `contents` input."
            )

        texts = request.texts
        if not texts:
            return EmbeddingResponse(embeddings=[], model=request.model or self.model)

        model_name = request.model or self.model or self.DEFAULT_MODEL
        model = self._get_or_create_model(model_name)

        loop = asyncio.get_running_loop()

        def _run_embedding():
            embeddings_generator = model.embed(texts)
            return [e.tolist() for e in embeddings_generator]

        embeddings = await loop.run_in_executor(None, _run_embedding)

        return EmbeddingResponse(
            embeddings=embeddings,
            model=model_name,
        )

    async def health_check(self) -> Dict[str, Any]:
        model_name = self.model or self.DEFAULT_MODEL
        try:
            model = self._get_or_create_model(model_name)
            return {
                "ok": True,
                "model": model_name,
                "provider": "fastembed",
                "dim": self.MODELS_INFO.get(model_name, self.dimensions or 1024),
            }
        except Exception as err:
            return {
                "ok": False,
                "error": str(err),
                "model": model_name,
                "provider": "fastembed",
            }
