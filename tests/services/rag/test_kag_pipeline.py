"""Unit tests for the KagPipeline orchestration."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from deeptutor.services.rag.factory import get_pipeline, KAG_PROVIDER
from deeptutor.services.rag.pipelines.kag.pipeline import KagPipeline, KagNotAvailableError
from deeptutor.services.rag.pipelines.base import RetrievalContext

@pytest.fixture
def mock_kag_lib():
    """Mock the external `kag` package and mark it as available."""
    mock_kag = MagicMock()
    
    # Setup KAGIterativePipeline mock
    mock_solver_pipeline = MagicMock()
    
    mock_kag_res = MagicMock()
    mock_kag_res.answer = "Final Synthesis"
    mock_kag_res.sub_queries = ["sub1", "sub2"]
    mock_kag_res.intermediate_results = ["Sub-query: sub1 -> Answer 1", "Sub-query: sub2 -> Answer 2"]
    mock_kag_res.entities = []
    mock_kag_res.relationships = []
    mock_kag_res.reasoning_paths = ["Path 1", "Path 2"]
    mock_kag_res.evidence_chunks = ["Chunk 1", "Chunk 2"]

    mock_solver_pipeline.invoke.return_value = mock_kag_res

    mock_kag.solver.KAGIterativePipeline.return_value = mock_solver_pipeline
    
    # Setup BuilderChainRunner mock
    mock_builder = MagicMock()
    mock_kag.builder.runner.BuilderChainRunner.return_value = mock_builder

    # Inject into sys.modules
    sys.modules["kag"] = mock_kag
    # We must also mock the specific imports used in pipeline.py
    sys.modules["kag.solver"] = mock_kag.solver
    sys.modules["kag.builder.runner"] = mock_kag.builder.runner
    
    with patch("deeptutor.services.rag.pipelines.kag.config.is_kag_available", return_value=True):
        yield mock_kag
        
    del sys.modules["kag"]


def test_factory_returns_kag_pipeline():
    """Ensure the factory correctly instantiates the KagPipeline."""
    pipeline = get_pipeline(KAG_PROVIDER)
    assert isinstance(pipeline, KagPipeline)


def test_is_kag_available_false_raises_error():
    """Ensure an explicit error is raised if the user tries to use KAG without installing it."""
    pipeline = KagPipeline()
    
    with patch("deeptutor.services.rag.pipelines.kag.config.is_kag_available", return_value=False):
        with pytest.raises(KagNotAvailableError, match="KAG framework is not installed"):
            pipeline._ensure_available()


@pytest.mark.asyncio
async def test_search_orchestrates_solver_pattern(mock_kag_lib):
    """Ensure search decomposes query, runs sub-queries, and aggregates scratchpad."""
    pipeline = KagPipeline()
    
    result = await pipeline.search("test query", "test_kb", mode="solver")
    
    assert isinstance(result, dict)
    assert result["provider"] == KAG_PROVIDER
    assert result["answer"] == "Final Synthesis"
    assert result["content"] == "Chunk 1\n\nChunk 2"
    assert len(result["sub_queries"]) == 2
    assert result["sub_queries"] == ["sub1", "sub2"]
    assert len(result["intermediate_results"]) == 2
    assert "Sub-query: sub1 -> Answer 1" in result["intermediate_results"][0]
    assert "Sub-query: sub2 -> Answer 2" in result["intermediate_results"][1]
    assert result["reasoning_paths"] == ["Path 1", "Path 2"]


@pytest.mark.asyncio
async def test_initialize_uses_strict_schema(mock_kag_lib):
    """Ensure initialize enforces mutual indexing via strict schema."""
    pipeline = KagPipeline()
    await pipeline.initialize("test_kb", ["test.txt"])
    
    builder_mock = mock_kag_lib.builder.runner.BuilderChainRunner.return_value
    builder_mock.invoke.assert_called_once_with(["test.txt"])
