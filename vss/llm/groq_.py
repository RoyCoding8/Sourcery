from __future__ import annotations

import json
import os

from pydantic import BaseModel


class GroqLLM:
    name: str = "groq"

    def __init__(self, model: str = "") -> None:
        from groq import AsyncGroq

        self.model = model or "llama-3.3-70b-versatile"
        self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    async def parse(self, schema: type[BaseModel], prompt: str) -> BaseModel:
        schema_json = json.dumps(schema.model_json_schema())
        full_prompt = f"{prompt}\n\nYou MUST respond in strictly valid JSON. The JSON object must match this exact schema:\n{schema_json}"
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            response_format={"type": "json_object"},
        )
        return schema.model_validate(json.loads(resp.choices[0].message.content or "{}"))

    async def complete(self, prompt: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
