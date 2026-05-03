from __future__ import annotations

import os

from pydantic import BaseModel


class AnthropicLLM:
    name: str = "anthropic"

    def __init__(self, model: str = "") -> None:
        import anthropic

        self.model = model or "claude-sonnet-4-20250514"
        self._client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def parse(self, schema: type[BaseModel], prompt: str) -> BaseModel:
        tool = {"name": "extract", "description": "Extract structured data", "input_schema": schema.model_json_schema()}
        resp = await self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            tools=[tool],
            tool_choice={"type": "tool", "name": "extract"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "tool_use":
                return schema.model_validate(block.input)
        msg = "No tool_use block in response"
        raise ValueError(msg)

    async def complete(self, prompt: str) -> str:
        resp = await self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
