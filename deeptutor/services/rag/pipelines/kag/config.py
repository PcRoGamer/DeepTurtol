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

def setup_kag_environment(workspace_dir: str):
    """Bridge DeepTutor's config to OpenSPG's environment requirements."""
    import os
    import json
    from deeptutor.services.config.runtime_settings import export_runtime_settings_to_env
    
    # 1. Export DeepTutor settings to os.environ so LiteLLM and OpenSPG can pick them up
    export_runtime_settings_to_env()
        
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
