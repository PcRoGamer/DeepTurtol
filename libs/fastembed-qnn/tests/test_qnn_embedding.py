import pytest
import numpy as np

from fastembed_qnn import QNNTextEmbedding


def test_qnn_embedding_initialization():
    model = QNNTextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    assert model is not None


def test_qnn_embedding_generation():
    model = QNNTextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    texts = ["Testing native fastembed-qnn acceleration"]
    embeddings = list(model.embed(texts))
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384
    # Verify vector unit L2 normalization
    norm = np.linalg.norm(embeddings[0])
    assert abs(norm - 1.0) < 1e-4
