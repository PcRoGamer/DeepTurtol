import logging
import numpy as np
from typing import Any, Dict

logger = logging.getLogger(__name__)


def setup_qnn_sdk_libraries() -> bool:
    """
    Initializes Qualcomm QNN SDK library paths (libQnnHtp.dll, libQnnGpu.dll, libQnnCpu.dll)
    so ONNX Runtime registers QNNExecutionProvider with native NPU execution on Snapdragon X Elite.
    """
    try:
        import onnxruntime_qnn
        onnxruntime_qnn.setup_library_path()
        logger.info("[OK] Qualcomm QNN SDK library paths initialized via onnxruntime_qnn")
        return True
    except ImportError:
        logger.debug("[NOTE] onnxruntime_qnn not installed. Running with default ONNX Runtime execution providers.")
        return False
    except Exception as err:
        logger.warning(f"[NOTE] QNN SDK library setup warning: {err}")
        return False


def apply_causal_onnx_position_ids_patch(model_instance: Any) -> bool:
    """
    Patches FastEmbed's ONNX text model runner to automatically construct and inject
    `position_ids` when required by causal language model ONNX graphs (e.g. Qwen3-Embedding).

    Standard FastEmbed only supplies `input_ids` and `attention_mask`. Causal ONNX models
    exported via Optimum expect `position_ids = np.arange(seq_len)`.
    """
    try:
        if not hasattr(model_instance, "model"):
            return False

        inner_model = model_instance.model
        if not hasattr(inner_model, "_preprocess_onnx_input"):
            return False

        orig_preprocess = inner_model._preprocess_onnx_input

        def _patched_preprocess(onnx_input: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
            onnx_input = orig_preprocess(onnx_input, **kwargs)
            if hasattr(inner_model, "model") and hasattr(inner_model.model, "get_inputs"):
                input_names = {node.name for node in inner_model.model.get_inputs()}
                if "position_ids" in input_names and "position_ids" not in onnx_input:
                    input_ids = onnx_input["input_ids"]
                    seq_len = input_ids.shape[1]
                    batch_size = input_ids.shape[0]
                    onnx_input["position_ids"] = np.tile(
                        np.arange(seq_len, dtype=np.int64), (batch_size, 1)
                    )
            return onnx_input

        inner_model._preprocess_onnx_input = _patched_preprocess
        logger.debug("Successfully applied position_ids preprocessing patch to ONNX runner")
        return True
    except Exception as err:
        logger.debug(f"Failed to apply position_ids patch: {err}")
        return False
