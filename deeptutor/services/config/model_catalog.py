from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any
from uuid import uuid4

from deeptutor.services.path_service import get_path_service

from .embedding_endpoint import normalize_embedding_endpoint_for_display

# Fallback only — frozen at admin scope at import time. Production code should
# enter through ``get_model_catalog_service()`` so the path is resolved from the
# current user's PathService on every call.
CATALOG_PATH = get_path_service().get_settings_file("model_catalog")


def _service_shell() -> dict[str, Any]:
    return {
        "active_profile_id": None,
        "active_model_id": None,
        "profiles": [],
    }


def _search_shell() -> dict[str, Any]:
    return {
        "active_profile_id": None,
        "profiles": [],
    }


import urllib.request
import logging

logger = logging.getLogger(__name__)


def is_free_opencode_model(model_id: str) -> bool:
    clean_id = str(model_id).lower().strip()
    return clean_id == "big-pickle" or clean_id.endswith("-free") or "-free-" in clean_id or ":free" in clean_id


def fetch_opencode_free_models(base_url: str = "https://opencode.ai/zen/v1") -> list[dict[str, str]]:
    """
    Queries OpenCode Zen models endpoint and returns strictly free models.
    """
    endpoint = f"{base_url.rstrip('/')}/models"
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "DeepTutor-Catalog-Fetcher"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                raw_models = data.get("data", [])
                free_models = []
                for m in raw_models:
                    mid = str(m.get("id", ""))
                    if is_free_opencode_model(mid):
                        name = f"{mid} (Default)" if mid == "big-pickle" else mid
                        free_models.append({
                            "id": f"llm-model-{mid.replace('.', '').replace(':', '-')}",
                            "name": name,
                            "model": mid
                        })
                if free_models:
                    return free_models
    except Exception as exc:
        logger.debug(f"Failed to fetch live free OpenCode models: {exc}")

    return [
        {"id": "llm-model-bigpickle", "name": "big-pickle (Default)", "model": "big-pickle"},
        {"id": "llm-model-deepseek-v4-flash-free", "name": "deepseek-v4-flash-free", "model": "deepseek-v4-flash-free"},
        {"id": "llm-model-mimo-v25-free", "name": "mimo-v2.5-free", "model": "mimo-v2.5-free"},
        {"id": "llm-model-ling-30-flash-free", "name": "ling-3.0-flash-free", "model": "ling-3.0-flash-free"},
        {"id": "llm-model-nemotron-3-ultra-free", "name": "nemotron-3-ultra-free", "model": "nemotron-3-ultra-free"},
        {"id": "llm-model-north-mini-code-free", "name": "north-mini-code-free", "model": "north-mini-code-free"},
        {"id": "llm-model-laguna-s-21-free", "name": "laguna-s-2.1-free", "model": "laguna-s-2.1-free"},
    ]


def _default_catalog() -> dict[str, Any]:
    return {
        "version": 1,
        "services": {
            "llm": {
                "active_profile_id": "llm-profile-opencode",
                "active_model_id": "llm-model-bigpickle",
                "rag_completion": {
                    "profile_id": "llm-profile-opencode",
                    "model_id": "llm-model-deepseek-v4-flash-free",
                },
                "profiles": [
                    {
                        "id": "llm-profile-opencode",
                        "name": "OpenCode Zen",
                        "binding": "opencode",
                        "base_url": "https://opencode.ai/zen/v1",
                        "api_key": "public",
                        "api_version": "",
                        "extra_headers": {},
                        "models": [
                            {"id": "llm-model-bigpickle", "name": "big-pickle (Default)", "model": "big-pickle"},
                            {"id": "llm-model-deepseek-v4-flash-free", "name": "deepseek-v4-flash-free", "model": "deepseek-v4-flash-free"},
                            {"id": "llm-model-mimo-v25-free", "name": "mimo-v2.5-free", "model": "mimo-v2.5-free"},
                            {"id": "llm-model-ling-30-flash-free", "name": "ling-3.0-flash-free", "model": "ling-3.0-flash-free"},
                            {"id": "llm-model-nemotron-3-ultra-free", "name": "nemotron-3-ultra-free", "model": "nemotron-3-ultra-free"},
                            {"id": "llm-model-north-mini-code-free", "name": "north-mini-code-free", "model": "north-mini-code-free"},
                            {"id": "llm-model-laguna-s-21-free", "name": "laguna-s-2.1-free", "model": "laguna-s-2.1-free"},
                        ]
                    }
                ]
            },
            "embedding": {
                "active_profile_id": None,
                "active_model_id": None,
                "profiles": [
                    {
                        "id": "embedding-profile-fastembed",
                        "name": "FastEmbed (Local NPU/ONNX)",
                        "binding": "fastembed",
                        "base_url": "http://localhost/fastembed",
                        "api_key": "local",
                        "api_version": "",
                        "extra_headers": {},
                        "models": [
                            {
                                "id": "embedding-model-qwen3-06b",
                                "name": "Qwen/Qwen3-Embedding-0.6B",
                                "model": "Qwen/Qwen3-Embedding-0.6B",
                                "dimension": "1024",
                            }
                        ]
                    }
                ]
            },
            "search": {
                "active_profile_id": "search-profile-duckduckgo",
                "profiles": [
                    {
                        "id": "search-profile-duckduckgo",
                        "name": "DuckDuckGo (Zero Setup)",
                        "provider": "duckduckgo",
                        "proxy": "",
                        "models": []
                    }
                ]
            },
            "tts": _service_shell(),
            # A ready-to-complete preset: Groq's free tier is suitable for
            # personal dictation, but its API key belongs to each user and
            # cannot be bundled with DeepTutor. Keep it inactive until the
            # user enters that key in Settings > Speech-to-Text.
            "stt": {
                "active_profile_id": None,
                "active_model_id": None,
                "profiles": [
                    {
                        "id": "stt-profile-groq-free",
                        "name": "Groq (Free Tier — add API key)",
                        "binding": "groq",
                        "base_url": "https://api.groq.com/openai/v1",
                        "api_key": "",
                        "requires_api_key": True,
                        "api_version": "",
                        "extra_headers": {},
                        "models": [
                            {
                                "id": "stt-model-groq-whisper-large-v3-turbo",
                                "name": "Whisper Large v3 Turbo (Free Tier)",
                                "model": "whisper-large-v3-turbo",
                            }
                        ],
                    }
                ],
            },
            "imagegen": _service_shell(),
            "videogen": _service_shell(),
        },
    }


class ModelCatalogService:
    _instances: dict[str, "ModelCatalogService"] = {}

    def __init__(self, path: Path | None = None):
        self.path = path or CATALOG_PATH
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls, path: Path | None = None) -> "ModelCatalogService":
        resolved = (path or get_path_service().get_settings_file("model_catalog")).resolve()
        key = str(resolved)
        if key not in cls._instances:
            cls._instances[key] = cls(resolved)
        return cls._instances[key]

    def load(self) -> dict[str, Any]:
        loaded = self._read_existing_catalog()
        if loaded:
            catalog = _default_catalog()
            catalog.update({k: v for k, v in loaded.items() if k != "services"})
            loaded_services = loaded.get("services", {})
            for svc_name, svc_data in loaded_services.items():
                if svc_name in catalog["services"]:
                    def_profiles = catalog["services"][svc_name].get("profiles", [])
                    existing_profiles = list(svc_data.get("profiles", []))
                    existing_pids = {p.get("id") for p in existing_profiles if p.get("id")}
                    for dp in def_profiles:
                        dpid = dp.get("id")
                        if dpid and dpid not in existing_pids:
                            existing_profiles.append(deepcopy(dp))
                        elif dpid:
                            for ep in existing_profiles:
                                if ep.get("id") == dpid:
                                    ex_models = list(ep.get("models", []))
                                    ex_model_keys = {m.get("model") or m.get("id") for m in ex_models}
                                    for dm in dp.get("models", []):
                                        m_key = dm.get("model") or dm.get("id")
                                        if m_key and m_key not in ex_model_keys:
                                            ex_models.append(deepcopy(dm))
                                    ep["models"] = ex_models
                    catalog["services"][svc_name].update(svc_data)
                    catalog["services"][svc_name]["profiles"] = existing_profiles
                else:
                    catalog["services"][svc_name] = svc_data

            merged_defaults = catalog != loaded
            before = deepcopy(catalog)
            self._normalize(catalog)
            if merged_defaults or catalog != before:
                self.save(catalog)
            return catalog

        catalog = _default_catalog()
        self._normalize(catalog)
        self.save(catalog)
        return catalog

    def _read_existing_catalog(self) -> dict[str, Any]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return {}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def save(self, catalog: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            normalized = deepcopy(catalog)
            self._normalize(normalized)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            temp_path = Path(temp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(normalized, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, self.path)
            finally:
                temp_path.unlink(missing_ok=True)
            return normalized

    def update(self, mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        with self._lock:
            catalog = self.load()
            mutator(catalog)
            return self.save(catalog)

    def apply(self, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
        current = self.save(catalog or self.load())
        return {"catalog_path": str(self.path), "services": list(current.get("services", {}))}

    def _normalize(self, catalog: dict[str, Any]) -> bool:
        services = catalog.setdefault("services", {})
        changed = False
        services.setdefault("llm", _service_shell())
        services.setdefault("embedding", _service_shell())
        services.setdefault("search", _search_shell())
        services.setdefault("tts", _service_shell())
        services.setdefault("stt", _service_shell())
        services.setdefault("imagegen", _service_shell())
        services.setdefault("videogen", _service_shell())
        for service_name in ("llm", "embedding", "search", "tts", "stt", "imagegen", "videogen"):
            service = services[service_name]
            profiles = service.setdefault("profiles", [])
            for profile in profiles:
                profile.setdefault("id", f"{service_name}-profile-{uuid4().hex[:8]}")
                profile.setdefault("name", "Untitled Profile")
                profile.setdefault("api_version", "")
                profile.setdefault("base_url", "")
                profile.setdefault("api_key", "")
                if service_name == "search":
                    profile.setdefault("provider", "brave")
                    profile.setdefault("proxy", "")
                    profile["models"] = []
                else:
                    profile.setdefault("binding", "openai")
                    profile.setdefault("extra_headers", {})
                    if service_name == "embedding":
                        before = str(profile.get("base_url") or "")
                        after = normalize_embedding_endpoint_for_display(
                            profile.get("binding"),
                            before,
                        )
                        if after != before:
                            profile["base_url"] = after
                            changed = True
                    models = profile.setdefault("models", [])
                    for model in models:
                        model.setdefault("id", f"{service_name}-model-{uuid4().hex[:8]}")
                        model.setdefault("name", model.get("model") or "Untitled Model")
                        model.setdefault("model", "")
                        if service_name == "embedding":
                            # Empty default → test_runner auto-fills from the
                            # actual API response on first connection test.
                            model.setdefault("dimension", "")
                            # CSV of supported dims discovered during the last
                            # successful "Test connection" — drives the UI
                            # dropdown. Empty when the model is not in any
                            # adapter's MODELS_INFO map.
                            model.setdefault("supported_dimensions", "")
                        elif service_name == "tts":
                            # Provider/model-specific free-form voice string
                            # (e.g. "alloy", "autumn", "model:voice").
                            model.setdefault("voice", "")
                            model.setdefault("response_format", "mp3")
                        elif service_name == "imagegen":
                            # Generation knobs; empty → provider default.
                            model.setdefault("size", "")
                            model.setdefault("quality", "")
                            model.setdefault("style", "")
                            model.setdefault("response_format", "")
                        elif service_name == "videogen":
                            model.setdefault("aspect_ratio", "")
                            model.setdefault("duration", "")
                            model.setdefault("resolution", "")
            profile_ids = {profile.get("id") for profile in profiles}
            if profiles and service.get("active_profile_id") not in profile_ids:
                # Bundled cloud presets can provide their endpoint/model without
                # bundling a user's secret. Do not auto-activate one until its
                # required key has been supplied.
                eligible_profiles = [
                    profile
                    for profile in profiles
                    if not profile.get("requires_api_key") or str(profile.get("api_key") or "").strip()
                ]
                service["active_profile_id"] = (
                    eligible_profiles[0]["id"] if eligible_profiles else None
                )
                changed = True
            if service_name in {"llm", "embedding", "tts", "stt", "imagegen", "videogen"}:
                active_profile = self.get_active_profile(catalog, service_name)
                models = (active_profile or {}).get("models") or []
                model_ids = {model.get("id") for model in models}
                if models and service.get("active_model_id") not in model_ids:
                    service["active_model_id"] = models[0]["id"]
                    changed = True
                elif not models and service.get("active_model_id") is not None:
                    service["active_model_id"] = None
                    changed = True
        return changed

    def get_active_profile(
        self, catalog: dict[str, Any], service_name: str
    ) -> dict[str, Any] | None:
        service = catalog.get("services", {}).get(service_name, {})
        active_id = service.get("active_profile_id")
        for profile in service.get("profiles", []):
            if profile.get("id") == active_id:
                return profile
        return None

    def get_active_model(self, catalog: dict[str, Any], service_name: str) -> dict[str, Any] | None:
        if service_name == "search":
            return None
        service = catalog.get("services", {}).get(service_name, {})
        active_model_id = service.get("active_model_id")
        profile = self.get_active_profile(catalog, service_name)
        if not profile:
            return None
        for model in profile.get("models", []):
            if model.get("id") == active_model_id:
                return model
        models = profile.get("models", [])
        return models[0] if models else None


def get_model_catalog_service() -> ModelCatalogService:
    try:
        from deeptutor.multi_user.context import get_current_user
        from deeptutor.multi_user.paths import get_admin_path_service

        if not get_current_user().is_admin:
            return ModelCatalogService.get_instance(
                get_admin_path_service().get_settings_file("model_catalog")
            )
    except Exception:
        pass
    return ModelCatalogService.get_instance(get_path_service().get_settings_file("model_catalog"))


def get_rag_completion_selection() -> dict[str, str] | None:
    """Read the ``rag_completion`` override from the active catalog.

    Returns a dict with ``profile_id`` and ``model_id`` keys, or ``None``
    when the catalog has no RAG-specific override.  RAG pipelines
    (GraphRAG / LightRAG) pass this to ``resolve_llm_runtime_config`` so
    indexing uses a different model than interactive chat.
    """
    try:
        catalog = get_model_catalog_service().load()
        llm = catalog.get("services", {}).get("llm", {})
        rag = llm.get("rag_completion")
        if rag and rag.get("profile_id") and rag.get("model_id"):
            return {"profile_id": rag["profile_id"], "model_id": rag["model_id"]}
    except Exception:
        pass
    return None


__all__ = ["CATALOG_PATH", "ModelCatalogService", "get_model_catalog_service", "get_rag_completion_selection"]
