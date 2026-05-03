from __future__ import annotations

import json
import os

from pydantic import BaseModel


class OllamaLLM:
    name: str = "ollama"

    def __init__(self, model: str = "") -> None:
        from ollama import AsyncClient

        self.model = model or "llama3.1"
        self._client = AsyncClient(host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    async def parse(self, schema: type[BaseModel], prompt: str) -> BaseModel:
        resp = await self._client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format=schema.model_json_schema(),
        )
        return schema.model_validate(json.loads(resp.message.content or "{}"))

    async def complete(self, prompt: str) -> str:
        resp = await self._client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.message.content or ""
