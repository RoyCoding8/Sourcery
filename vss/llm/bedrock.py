from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from pydantic import BaseModel

log = logging.getLogger(__name__)


class BedrockLLM:
    name = "bedrock"

    def __init__(self, model: str = "") -> None:
        import boto3

        self.model = (
            model or os.getenv("BEDROCK_MODELS", "anthropic.claude-3-5-sonnet-20241022-v2:0").split(",")[0].strip()
        )
        self._client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))

    async def _converse(self, prompt: str, system: str | None = None, tool_config: dict | None = None) -> dict:
        kw: dict = {
            "modelId": self.model,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
        }
        if system:
            kw["system"] = [{"text": system}]
        if tool_config:
            kw["toolConfig"] = tool_config
        return await asyncio.to_thread(self._client.converse, **kw)

    def _extract_json(self, text: str, schema: type[BaseModel]) -> BaseModel | None:
        for pat in (re.compile(r"```(?:json)?\s*([\s\S]*?)```"), re.compile(r"(\{[\s\S]*\})")):
            m = pat.search(text)
            if not m:
                continue
            try:
                return schema.model_validate_json(m.group(1).strip())
            except (TypeError, ValueError):
                pass
            try:
                return schema.model_validate(json.loads(m.group(1).strip()))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return None

    async def parse(self, schema: type[BaseModel], prompt: str) -> BaseModel:
        system = "You are a structured data extraction assistant. Follow all instructions precisely. Always call the provided tool."
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "extract",
                        "description": f"Extract structured {schema.__name__} data from the text. Always call this tool with your answer.",
                        "inputSchema": {"json": schema.model_json_schema()},
                    },
                }
            ],
            "toolChoice": {"any": {}},
        }
        try:
            resp = await self._converse(prompt, system=system, tool_config=tool_config)
            for block in resp["output"]["message"]["content"]:
                if "toolUse" in block:
                    return schema.model_validate(block["toolUse"]["input"])
            text_blocks = [b["text"] for b in resp["output"]["message"]["content"] if "text" in b]
            for t in text_blocks:
                result = self._extract_json(t, schema)
                if result:
                    return result
        except Exception as e:
            log.warning("tool-call parse failed for %s (%s): %s", schema.__name__, self.model, e)

        log.info("falling back to text-mode JSON extraction for %s", schema.__name__)
        schema_hint = json.dumps(schema.model_json_schema(), indent=2)
        fallback_prompt = f"{prompt}\n\nReturn your answer as a single JSON object matching this schema:\n{schema_hint}"
        resp = await self._converse(fallback_prompt, system=system)
        text = resp["output"]["message"]["content"][0].get("text", "")
        result = self._extract_json(text, schema)
        if result:
            return result
        raise ValueError(f"Bedrock ({self.model}): could not extract {schema.__name__} from response")

    async def complete(self, prompt: str) -> str:
        resp = await self._converse(prompt)
        return resp["output"]["message"]["content"][0]["text"]
