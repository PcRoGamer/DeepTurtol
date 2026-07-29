"""Unit tests for the KagPipeline orchestration."""

import sys
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from deeptutor.services.rag.factory import get_pipeline, KAG_PROVIDER
from deeptutor.services.rag.pipelines.kag.pipeline import KagPipeline, KagNotAvailableError
from deeptutor.services.rag.pipelines.base import RetrievalContext
from deeptutor.services.rag.pipelines.kag.config import resolve_kag_llm_settings

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


def test_kag_uses_the_rag_completion_provider(monkeypatch: pytest.MonkeyPatch):
    """KAG must not default to api.openai.com for an OpenAI-compatible provider."""
    import deeptutor.services.config as config_service
    import deeptutor.services.config.model_catalog as catalog

    selection = {"profile_id": "zen", "model_id": "deepseek"}
    monkeypatch.setattr(catalog, "get_rag_completion_selection", lambda: selection)
    resolver = MagicMock(
        return_value=SimpleNamespace(
            effective_url="https://opencode.ai/zen/v1",
            base_url="https://ignored.example/v1",
            model="deepseek-v4-flash-free",
            api_key="public",
        )
    )
    monkeypatch.setattr(config_service, "resolve_llm_runtime_config", resolver)

    assert resolve_kag_llm_settings() == (
        "https://opencode.ai/zen/v1",
        "deepseek-v4-flash-free",
        "public",
    )
    resolver.assert_called_once_with(llm_selection=selection)


def test_search_reads_the_selected_kb_instead_of_kag_demo_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    raw_dir = tmp_path / "handbooks" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "bdes.txt").write_text(
        "Bachelor of Design (B-DES) is a 300 credit point undergraduate degree. "
        "It is delivered on campus at Parkville.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "deeptutor.services.rag.pipelines.kag.config.is_kag_available", lambda: True
    )

    result = asyncio.run(
        KagPipeline(kb_base_dir=str(tmp_path)).search(
            "tell me about B-DES", "handbooks"
        )
    )

    assert "300 credit point" in result["content"]
    assert "Yu'ebao" not in result["content"]
    assert result["sources"][0]["title"] == "bdes.txt"


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
