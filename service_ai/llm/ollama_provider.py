"""Proveedor Ollama: modelos locales, sin API key. Util para probar sin coste."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import ChatMessage, LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model: str, base_url: str = "", timeout: int = 120) -> None:
        self._model = model or "llama3.1"
        self._base = (base_url or "http://localhost:11434").rstrip("/")
        self._timeout = timeout

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", f"{self._base}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for linea in resp.aiter_lines():
                    if not linea.strip():
                        continue
                    try:
                        data = json.loads(linea)
                        texto = data.get("message", {}).get("content")
                    except json.JSONDecodeError:
                        continue
                    if texto:
                        yield texto
