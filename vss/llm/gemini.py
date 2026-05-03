from __future__ import annotations

import json
import os

from pydantic import BaseModel


class GeminiLLM:
    name: str = "gemini"

    def __init__(self, model: str = "") -> None:
        from google import genai

        self.model = model or "gemini-2.0-flash"
        self._client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async def parse(self, schema: type[BaseModel], prompt: str) -> BaseModel:
        from google.genai.types import GenerateContentConfig

        resp = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
        )
        return schema.model_validate(json.loads(resp.text))

    async def complete(self, prompt: str) -> str:
        resp = await self._client.aio.models.generate_content(model=self.model, contents=prompt)
        return resp.text or ""
