from __future__ import annotations

import os
import re

from dotenv import load_dotenv

load_dotenv()

_TOOL_CAPABLE = re.compile(r"(?:us\.)?(?:amazon\.nova|meta\.llama|qwen\.|anthropic\.claude)", re.I)

PROVIDERS = ("bedrock", "anthropic", "openai", "gemini", "groq", "ollama", "stub")

_CRED_KEYS: dict[str, tuple[str, ...]] = {
    "bedrock": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "ollama": ("OLLAMA_BASE_URL",),
    "stub": (),
}


def models_for(provider: str) -> list[str]:
    raw = os.getenv(f"{provider.upper()}_MODELS", "")
    return [m.strip() for m in raw.split(",") if m.strip()]


def has_creds(provider: str) -> bool:
    if provider == "stub":
        return True
    return all(os.getenv(k) for k in _CRED_KEYS.get(provider, ()))


def default_provider() -> str:
    explicit = os.getenv("LLM_PROVIDER", "").strip()
    if explicit and explicit in PROVIDERS:
        return explicit
    for p in PROVIDERS:
        if has_creds(p) and p != "stub":
            return p
    return "stub"


def default_model(provider: str) -> str:
    explicit = os.getenv("LLM_MODEL", "").strip()
    if explicit:
        return explicit
    models = models_for(provider)
    return models[0] if models else ""


def tool_model(provider: str) -> str | None:
    for m in models_for(provider):
        if _TOOL_CAPABLE.search(m):
            return m
    return None
