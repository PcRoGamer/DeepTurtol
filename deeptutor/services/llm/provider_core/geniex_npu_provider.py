"""Qualcomm GenieX NPU Provider Implementation."""

from __future__ import annotations

import asyncio
from typing import Any, Sequence, List, Dict

from deeptutor.services.llm.geniex_provider import complete as geniex_complete
from deeptutor.services.llm.provider_core.base import LLMProvider, LLMResponse


class GenieXNPUProvider(LLMProvider):
    """LLM Provider executing models directly on Qualcomm Hexagon NPU via GenieX."""

    def __init__(self, default_model: str | None = None) -> None:
        super().__init__()
        self.default_model = default_model or "local/gemma4-e2b-qat"

    def get_default_model(self) -> str:
        return self.default_model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        model_name = model or self.default_model
        
        system_prompt = "You are a helpful AI assistant."
        prompt_text = ""
        
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                prompt_text = content

        text_result = await geniex_complete(
            prompt=prompt_text,
            system_prompt=system_prompt,
            model=model_name,
            compute="npu",
            max_tokens=max_tokens or 1024,
            messages=messages
        )

        return LLMResponse(
            content=text_result,
            tool_calls=[],
            finish_reason="stop"
        )

    async def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        msg_list = list(messages) if isinstance(messages, Sequence) else []
        return await self.chat(messages=msg_list, tools=list(tools) if tools else None, **kwargs)
