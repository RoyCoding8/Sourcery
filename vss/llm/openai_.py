from __future__ import annotations

import json
import os

from pydantic import BaseModel


class OpenAILLM:
    name: str = "openai"

    def __init__(self, model: str = "") -> None:
        from openai import AsyncOpenAI

        self.model = model or "gpt-4o"
        self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def parse(self, schema: type[BaseModel], prompt: str) -> BaseModel:
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "type": "function",
                    "function": {"name": "extract", "parameters": schema.model_json_schema()},
                }
            ],
            tool_choice={"type": "function", "function": {"name": "extract"}},
        )
        call = resp.choices[0].message.tool_calls[0]
        return schema.model_validate(json.loads(call.function.arguments))

    async def complete(self, prompt: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
