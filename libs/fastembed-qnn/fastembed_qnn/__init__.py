"""
fastembed-qnn
-------------
Native Qualcomm QNN NPU Hardware Acceleration for FastEmbed on Snapdragon X Elite laptops (ARM64 Windows).
"""

from .embedding import QNNTextEmbedding
from .patcher import apply_causal_onnx_position_ids_patch, setup_qnn_sdk_libraries

__version__ = "0.1.0"
__all__ = [
    "QNNTextEmbedding",
    "setup_qnn_sdk_libraries",
    "apply_causal_onnx_position_ids_patch",
]
