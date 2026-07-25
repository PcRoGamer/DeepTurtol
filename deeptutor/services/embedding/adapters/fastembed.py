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
            from fastembed.common.model_description import ModelSource, PoolingType
        except ImportError as err:
            raise ImportError(
                "fastembed library is required for FastEmbedAdapter. "
                "Install it with `pip install fastembed`."
            ) from err

        # Filter requested execution providers against host ONNX Runtime capabilities
        try:
            import onnxruntime as ort
            available_providers = set(ort.get_available_providers())
            valid_providers = [p for p in self.DEFAULT_PROVIDERS if p in available_providers]
            if not valid_providers:
                valid_providers = ["CPUExecutionProvider"]
        except Exception:
            valid_providers = ["CPUExecutionProvider"]

        # Dynamically register custom model if not in FastEmbed's default supported list
        try:
            supported_names = [m["model"] for m in TextEmbedding.list_supported_models()]
            if model_name not in supported_names:
                dim = self.MODELS_INFO.get(model_name, self.dimensions or 1024)
                TextEmbedding.add_custom_model(
                    model=model_name,
                    pooling=PoolingType.MEAN,
                    normalization=True,
                    sources=ModelSource(hf=model_name),
                    dim=dim,
                    model_file="model.onnx",
                )
                logger.info(f"Registered model '{model_name}' (dim={dim}) into FastEmbed registry")
        except Exception as reg_err:
            logger.debug(f"Custom model registration hint for '{model_name}': {reg_err}")

        logger.info(
            f"Initializing FastEmbed TextEmbedding model '{model_name}' "
            f"with valid providers={valid_providers}"
        )
        try:
            model = TextEmbedding(
                model_name=model_name,
                providers=valid_providers,
            )
        except Exception as exc:
            logger.warning(
                f"Failed to initialize FastEmbed with providers {valid_providers}: {exc}. "
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
        model_name = request.model or self.model or self.DEFAULT_MODEL
        if not texts:
            dim = self.MODELS_INFO.get(model_name, self.dimensions or 1024)
            return EmbeddingResponse(
                embeddings=[],
                model=model_name,
                dimensions=dim,
                usage={"prompt_tokens": 0, "total_tokens": 0},
            )

        model = self._get_or_create_model(model_name)
        loop = asyncio.get_running_loop()

        def _run_embedding():
            embeddings_generator = model.embed(texts)
            return [e.tolist() for e in embeddings_generator]

        embeddings = await loop.run_in_executor(None, _run_embedding)
        dim = len(embeddings[0]) if embeddings else (self.dimensions or 1024)
        total_tokens = sum(len(t.split()) for t in texts)
        return EmbeddingResponse(
            embeddings=embeddings,
            model=model_name,
            dimensions=dim,
            usage={"prompt_tokens": total_tokens, "total_tokens": total_tokens},
        )

    def get_model_info(self) -> Dict[str, Any]:
        model_name = self.model or self.DEFAULT_MODEL
        return {
            "model": model_name,
            "dimensions": self.MODELS_INFO.get(model_name, self.dimensions or 1024),
            "provider": "fastembed",
            "is_local": True,
        }

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
