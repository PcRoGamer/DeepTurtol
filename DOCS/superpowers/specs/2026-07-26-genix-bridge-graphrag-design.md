# GenieX HTTP Bridge + Ollama Fallback for GraphRAG

## Problem

GraphRAG's indexing pipeline uses LiteLLM internally, which requires an
OpenAI-compatible HTTP API for LLM calls. DeepTutor's GenieX integration
(`geniex_provider.py`) works via CLI subprocess (`geniex.exe infer`), which
satisfies chat but not GraphRAG. The `settings.yaml` generated for GraphRAG
references `http://localhost/geniex` — a dead URL with nothing listening.

Result: GraphRAG indexing fails with `Connection error` at the `extract_graph`
step.

## Solution

Two components plus config wiring:

### 1. GenieX HTTP Bridge

**File**: `deeptutor/services/llm/geniex_bridge.py`

A lightweight FastAPI/Starlette server (~100 lines) that wraps the GenieX CLI
into an OpenAI-compatible HTTP API.

**Endpoints**:
- `POST /v1/chat/completions` — proxies to `geniex.exe infer`
- `GET /health` — returns 200 when the bridge is alive

**Request flow**:
1. Receive OpenAI-format request (`model`, `messages`, `max_tokens`)
2. Extract system message and user prompt from `messages` array
3. Call `geniex.exe infer <model> --compute npu -s <system> -p <prompt> --max-tokens <N> --think=false --skip-update`
4. Parse output, strip ANSI codes and timing lines (reuse `_strip_ansi` from `geniex_provider.py`)
5. Return OpenAI-format JSON response

**Port**: Configurable via `GENIEX_BRIDGE_PORT` env var, default `18080`.

**Dependencies**: Only `aiohttp` (already a transitive dep via litellm) or
`uvicorn`+`starlette` (already in the project). No new dependencies.

### 2. LLM Server Manager

**File**: `deeptutor/services/llm/llm_server_manager.py`

Manages the lifecycle of the LLM HTTP server used by GraphRAG.

**Responsibilities**:
- At backend startup, determine active LLM provider
- If `geniex_npu`: start GenieX bridge subprocess, wait for `/health` 200
- If GenieX unavailable (executable not found): fall back to Ollama via
  `ensure_local_slm_running()`
- Store the active endpoint URL for downstream consumers (GraphRAG config)
- Handle graceful shutdown on process exit

**Interface**:
```python
class LLMServerManager:
    def start(self) -> str:
        """Start the LLM server, return the base URL (e.g. 'http://localhost:18080')."""

    def stop(self) -> None:
        """Shut down the managed server process."""

    @property
    def endpoint_url(self) -> str | None:
        """The active OpenAI-compatible base URL, or None if not started."""
```

**Singleton**: Module-level `get_llm_server_manager()` returns a process-wide
instance (mirrors `_FASTEMBED_MODEL_CACHE` pattern).

### 3. Backend Startup Integration

**File**: `deeptutor/api/run_server.py` (modify)

After `configure_logging()` and before `uvicorn.run()`:
```python
from deeptutor.services.llm.llm_server_manager import get_llm_server_manager
manager = get_llm_server_manager()
endpoint = manager.start()
```

**File**: `deeptutor/runtime/launcher.py` (modify)

In the `start()` function, after backend process is spawned, the manager is
initialized inside the backend process itself (not the launcher). This keeps
the launcher lightweight.

### 4. GraphRAG Config Wiring

**File**: `deeptutor/services/rag/pipelines/graphrag/config.py` (modify)

In `build_settings()`, resolve the LLM endpoint:
```python
from deeptutor.services.llm.llm_server_manager import get_llm_server_manager

manager = get_llm_server_manager()
llm_base = manager.endpoint_url  # e.g. "http://localhost:18080"
# If manager not started (e.g. CLI mode), fall back to existing behavior
if llm_base is None:
    llm_base = getattr(llm_cfg, "effective_url", None) or getattr(llm_cfg, "base_url", None)
```

Model name mapping:
- GenieX bridge: `local/gemma4-e2b-qat` (same as CLI)
- Ollama fallback: `gemma4-e2b-qat` (without `local/` prefix)

## Data Flow

```
GraphRAG indexing
  → LiteLLM
    → http://localhost:18080/v1/chat/completions
      → GenieX Bridge (FastAPI)
        → geniex.exe infer local/gemma4-e2b-qat --compute npu ...
          → NPU hardware

Fallback (GenieX unavailable):
GraphRAG indexing
  → LiteLLM
    → http://localhost:11434/v1/chat/completions
      → Ollama (auto-started via ensure_local_slm_running)
```

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `deeptutor/services/llm/geniex_bridge.py` | **Create** | GenieX CLI → HTTP bridge server |
| `deeptutor/services/llm/llm_server_manager.py` | **Create** | Lifecycle manager for bridge/Ollama |
| `deeptutor/api/run_server.py` | **Modify** | Call manager at startup |
| `deeptutor/services/rag/pipelines/graphrag/config.py` | **Modify** | Resolve endpoint from manager |

## Error Handling

- Bridge fails to start → fall back to Ollama automatically
- Ollama not installed → log warning, GraphRAG indexing will fail with clear
  error message
- Bridge crashes during indexing → LiteLLM retries, then GraphRAG reports
  failure with the underlying error
- Both unavailable → existing behavior (GraphRAG reports connection error)

## Testing

- Unit test for bridge request/response format
- Integration test: bridge starts, accepts OpenAI-format request, returns valid response
- Integration test: manager falls back to Ollama when GenieX not found
- Manual test: GraphRAG KB creation with GenieX bridge

## Out of Scope

- Embedding model auto-start (fastembed-qnn is in-process, already cached)
- Modifying GenieX CLI behavior
- Multi-model support in the bridge (single model per bridge instance)
