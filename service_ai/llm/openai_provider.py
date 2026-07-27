"""Proveedor OpenAI (y APIs compatibles vic LLM_BASE_URL). Streaming SSE."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import ChatMessage, LLMConfigError, LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str = "", timeout: int = 60) -> None:
        if not api_key:
            raise LLMConfigError("LLM_PROVIDER=openai requiere LLM_API_KEY.")
        self._api_key = api_key
        self._model = model or "gpt-4o-mini"
        self._base = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST", f"{self._base}/chat/completions", json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for linea in resp.aiter_lines():
                    if not linea.startswith("data: "):
                        continue
                    data = linea.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"].get("content")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if delta:
                        yield delta
