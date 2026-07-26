"""Factory for services-layer provider runtime objects."""

from __future__ import annotations

from deeptutor.services.llm.config import LLMConfig, get_llm_config
from deeptutor.services.llm.provider_core import (
    AnthropicProvider,
    AzureOpenAIProvider,
    GenerationSettings,
    GenieXNPUProvider,
    GitHubCopilotProvider,
    LLMProvider,
    OpenAICodexProvider,
    OpenAICompatProvider,
)
from deeptutor.services.llm.utils import sanitize_url
from deeptutor.services.provider_registry import find_by_name


def get_runtime_provider(config: LLMConfig | None = None) -> LLMProvider:
    """Build the authoritative services-layer provider for the supplied config."""
    llm_config = config or get_llm_config()
    provider_name = getattr(llm_config, "provider_name", None) or getattr(llm_config, "binding", "")
    spec = find_by_name(provider_name)
    backend = spec.backend if spec else "openai_compat"

    raw_base = getattr(llm_config, "effective_url", None) or getattr(llm_config, "base_url", None) or None
    sanitized_base = sanitize_url(raw_base) if raw_base else None

    if backend == "geniex_npu":
        provider: LLMProvider = GenieXNPUProvider(default_model=getattr(llm_config, "model", None))
    elif backend == "openai_codex":
        provider = OpenAICodexProvider(default_model=getattr(llm_config, "model", None))
    elif backend == "github_copilot":
        provider = GitHubCopilotProvider(default_model=getattr(llm_config, "model", None))
    elif backend == "azure_openai":
        provider = AzureOpenAIProvider(
            api_key=getattr(llm_config, "api_key", None) or "",
            api_base=sanitized_base or "",
            default_model=getattr(llm_config, "model", None),
            extra_headers=getattr(llm_config, "extra_headers", None),
        )
    elif backend == "anthropic":
        provider = AnthropicProvider(
            api_key=getattr(llm_config, "api_key", None),
            api_base=sanitized_base,
            default_model=getattr(llm_config, "model", None),
            extra_headers=getattr(llm_config, "extra_headers", None),
            supports_prompt_caching=bool(spec and spec.supports_prompt_caching),
        )
    else:
        provider = OpenAICompatProvider(
            api_key=getattr(llm_config, "api_key", None),
            api_base=sanitized_base,
            default_model=getattr(llm_config, "model", None),
            extra_headers=getattr(llm_config, "extra_headers", None),
            spec=spec,
            provider_name=provider_name,
        )

    provider.generation = GenerationSettings(
        temperature=getattr(llm_config, "temperature", 0.7),
        max_tokens=getattr(llm_config, "max_tokens", 4096),
        reasoning_effort=getattr(llm_config, "reasoning_effort", None),
    )
    return provider
