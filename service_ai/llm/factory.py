"""
Factoria de proveedores segun el .env.

Cambiar de LLM son dos variables (LLM_PROVIDER, LLM_MODEL) y su LLM_API_KEY, sin
tocar codigo. El default es 'fake', que arranca sin red ni credenciales. Si se
pide un proveedor real sin API key, se falla al arrancar con un mensaje claro en
vez de degradarse en silencio.
"""
from __future__ import annotations

from ..config import Settings
from .anthropic_provider import AnthropicProvider
from .base import LLMConfigError, LLMProvider
from .fake import FakeProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

PROVEEDORES = ("fake", "openai", "anthropic", "gemini", "ollama")


def build_provider(settings: Settings) -> LLMProvider:
    nombre = (settings.llm_provider or "fake").strip().lower()
    if nombre == "fake":
        return FakeProvider(token_delay_ms=settings.fake_llm_token_delay_ms)
    if nombre == "openai":
        return OpenAIProvider(settings.llm_api_key, settings.llm_model,
                              settings.llm_base_url, settings.llm_timeout_seconds)
    if nombre == "anthropic":
        return AnthropicProvider(settings.llm_api_key, settings.llm_model,
                                 settings.llm_base_url, settings.llm_timeout_seconds)
    if nombre == "gemini":
        return GeminiProvider(settings.llm_api_key, settings.llm_model,
                              settings.llm_base_url, settings.llm_timeout_seconds)
    if nombre == "ollama":
        return OllamaProvider(settings.llm_model, settings.llm_base_url,
                              settings.llm_timeout_seconds)
    raise LLMConfigError(
        f"LLM_PROVIDER='{nombre}' no reconocido. Validos: {', '.join(PROVEEDORES)}."
    )
