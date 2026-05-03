from __future__ import annotations

from importlib import import_module
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from vss.settings import default_model, default_provider

_CLIENTS = {
    "anthropic": ("vss.llm.anthropic_", "AnthropicLLM"),
    "bedrock": ("vss.llm.bedrock", "BedrockLLM"),
    "gemini": ("vss.llm.gemini", "GeminiLLM"),
    "groq": ("vss.llm.groq_", "GroqLLM"),
    "ollama": ("vss.llm.ollama_", "OllamaLLM"),
    "openai": ("vss.llm.openai_", "OpenAILLM"),
    "stub": ("vss.llm.stub", "StubLLM"),
}


@runtime_checkable
class LLMClient(Protocol):
    name: str
    model: str

    async def parse(self, schema: type[BaseModel], prompt: str) -> BaseModel: ...
    async def complete(self, prompt: str) -> str: ...


def get_llm(provider: str | None = None, model: str | None = None) -> LLMClient:
    prov = provider or default_provider()
    mdl = model or default_model(prov)

    try:
        module, class_name = _CLIENTS[prov]
    except KeyError as e:
        msg = f"Unknown provider: {prov}"
        raise ValueError(msg) from e
    try:
        return getattr(import_module(module), class_name)(model=mdl)
    except ModuleNotFoundError as e:
        msg = (
            f"Provider '{prov}' needs optional dependencies. Install sourcery-tool[{prov}] or sourcery-tool[all-llms]."
        )
        raise ImportError(msg) from e
