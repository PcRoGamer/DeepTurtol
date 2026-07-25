import logging
from typing import Any, Iterable, List, Optional, Union
import numpy as np

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

from .patcher import apply_causal_onnx_position_ids_patch, setup_qnn_sdk_libraries

logger = logging.getLogger(__name__)


class QNNTextEmbedding:
    """
    High-performance wrapper for FastEmbed with Qualcomm QNN SDK NPU hardware acceleration
    and automatic causal ONNX model support (e.g. Qwen3-Embedding).
    """

    MODEL_MAPPINGS = {
        "Qwen/Qwen3-Embedding-0.6B": {
            "hf": "shawnw3i/Qwen3-Embedding-0.6B-ONNX",
            "dim": 1024,
            "pooling": getattr(PoolingType, "LAST_TOKEN", PoolingType.MEAN),
            "model_file": "model.onnx",
        },
        "Qwen/Qwen3-Embedding-4B": {
            "hf": "shawnw3i/Qwen3-Embedding-4B-ONNX",
            "dim": 2560,
            "pooling": getattr(PoolingType, "LAST_TOKEN", PoolingType.MEAN),
            "model_file": "model.onnx",
        },
    }

    DEFAULT_PROVIDERS = [
        "QNNExecutionProvider",
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Embedding-0.6B",
        providers: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self.model_name = model_name

        # 1. Setup QNN SDK library paths on Snapdragon X Elite
        setup_qnn_sdk_libraries()

        # 2. Filter requested providers against host ONNX Runtime
        try:
            import onnxruntime as ort
            avail = set(ort.get_available_providers())
            target_providers = providers or self.DEFAULT_PROVIDERS
            valid_providers = [p for p in target_providers if p in avail]
            if not valid_providers:
                valid_providers = ["CPUExecutionProvider"]
        except Exception:
            valid_providers = ["CPUExecutionProvider"]

        self.valid_providers = valid_providers

        # 3. Dynamic Custom Model Registration if needed
        self._register_custom_model_if_needed(model_name)

        # 4. Instantiate FastEmbed model with QNN providers
        try:
            self._model = TextEmbedding(
                model_name=model_name,
                providers=valid_providers,
                **kwargs,
            )
        except Exception as exc:
            logger.warning(
                f"Failed to load '{model_name}' with providers {valid_providers}: {exc}. "
                "Falling back to default initialization."
            )
            self._model = TextEmbedding(model_name=model_name, **kwargs)

        # 5. Apply causal position_ids tensor patch for ONNX graphs requiring it
        apply_causal_onnx_position_ids_patch(self._model)

    def _register_custom_model_if_needed(self, model_name: str) -> None:
        try:
            supported_names = [m["model"] for m in TextEmbedding.list_supported_models()]
            if model_name in supported_names:
                return

            info = self.MODEL_MAPPINGS.get(model_name, {})
            hf_source = info.get("hf", model_name)
            dim = info.get("dim", 1024)
            pooling = info.get(
                "pooling",
                getattr(PoolingType, "LAST_TOKEN", PoolingType.MEAN) if "qwen" in model_name.lower() else PoolingType.MEAN,
            )
            model_file = info.get("model_file", "model.onnx")

            TextEmbedding.add_custom_model(
                model=model_name,
                pooling=pooling,
                normalization=True,
                sources=ModelSource(hf=hf_source),
                dim=dim,
                model_file=model_file,
            )
            logger.info(f"Registered custom model '{model_name}' -> '{hf_source}' (dim={dim}) in FastEmbed registry")
        except Exception as reg_err:
            logger.debug(f"Custom model registration hint: {reg_err}")

    def embed(
        self,
        documents: Union[str, Iterable[str]],
        batch_size: int = 256,
        parallel: Optional[int] = None,
        **kwargs: Any,
    ) -> Iterable[np.ndarray]:
        """
        Generates dense vector embeddings for documents.
        """
        if isinstance(documents, str):
            documents = [documents]
        return self._model.embed(
            documents=documents,
            batch_size=batch_size,
            parallel=parallel,
            **kwargs,
        )
