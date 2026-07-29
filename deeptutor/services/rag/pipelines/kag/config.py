"""Configuration and dependency checks for the KAG pipeline."""

import logging

logger = logging.getLogger(__name__)

SUPPORTED_MODES = ("solver", "naive")
DEFAULT_MODE = "solver"


def is_kag_available() -> bool:
    """Return True if the KAG (Knowledge Augmented Generation) dependency is installed."""
    try:
        import os
        os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
        import kag  # noqa: F401
        return True
    except ImportError:
        return False


def resolve_kag_llm_settings() -> tuple[str, str, str]:
    """Return the selected DeepTutor RAG model in KAG's client format.

    KAG's ``OpenAIClient`` does not read DeepTutor's provider catalog.  In
    particular, it historically read ``OPENAI_API_BASE`` while DeepTutor
    exports ``OPENAI_BASE_URL``.  That made KAG silently use api.openai.com
    and send an OpenCode Zen ``public`` token there.  Resolve the catalog
    explicitly so KAG always uses the configured RAG-completion provider.
    """
    from deeptutor.services.config import resolve_llm_runtime_config
    from deeptutor.services.config.model_catalog import get_rag_completion_selection

    resolved = resolve_llm_runtime_config(
        llm_selection=get_rag_completion_selection()
    )
    base_url = (resolved.effective_url or resolved.base_url or "").strip()
    if not base_url:
        raise RuntimeError(
            "No LLM endpoint is configured for KAG. Configure it in Settings > Catalog."
        )
    if not resolved.model:
        raise RuntimeError(
            "No LLM model is configured for KAG. Configure it in Settings > Catalog."
        )
    return base_url, resolved.model, resolved.api_key or "sk-no-key-required"


def setup_kag_environment(workspace_dir: str):
    """Bridge DeepTutor's config to OpenSPG's environment requirements."""
    import os
    import json
    from deeptutor.services.config.runtime_settings import export_runtime_settings_to_env
    
    # 1. Export DeepTutor settings to os.environ so LiteLLM and OpenSPG can pick them up
    export_runtime_settings_to_env()
    base_url, model, api_key = resolve_kag_llm_settings()
    # KAG uses a different environment-variable spelling from the OpenAI SDK.
    # Set both aliases for its builder components and any provider helpers.
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["OPENAI_API_BASE"] = base_url
    os.environ["LLM_MODEL"] = model
        
    # 2. Setup standard KAG Project structure in the workspace if missing
    kag_dir = os.path.join(workspace_dir, ".kag")
    os.makedirs(kag_dir, exist_ok=True)
    
    # Generate a default schema.json for OpenSPG mutual indexing if missing
    schema_path = os.path.join(kag_dir, "schema.json")
    if not os.path.exists(schema_path):
        default_schema = {
            "entities": [{"name": "Concept"}, {"name": "Document"}],
            "relations": [{"subject": "Concept", "predicate": "relatedTo", "object": "Concept"}]
        }
        with open(schema_path, "w") as f:
            json.dump(default_schema, f, indent=2)
            
    # Set OpenSPG KAG Project path
    os.environ["KAG_PROJECT_DIR"] = kag_dir
