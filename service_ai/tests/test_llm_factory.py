import pytest

from service_ai.config import Settings
from service_ai.llm.base import ChatMessage, LLMConfigError
from service_ai.llm.factory import build_provider
from service_ai.llm.fake import FakeProvider


def _settings(**kw) -> Settings:
    base = dict(llm_provider="fake", llm_api_key="", llm_model="", database_url="sqlite:////tmp/x")
    base.update(kw)
    return Settings(**base)


def test_por_defecto_devuelve_el_proveedor_falso():
    assert isinstance(build_provider(_settings()), FakeProvider)


def test_cambiar_proveedor_es_cambiar_una_variable():
    p = build_provider(_settings(llm_provider="openai", llm_api_key="sk-test"))
    assert p.name == "openai"


def test_proveedor_real_sin_api_key_falla_al_construir():
    with pytest.raises(LLMConfigError):
        build_provider(_settings(llm_provider="anthropic", llm_api_key=""))


def test_proveedor_desconocido_falla():
    with pytest.raises(LLMConfigError):
        build_provider(_settings(llm_provider="inexistente"))


async def test_el_fake_emite_token_a_token():
    provider = FakeProvider(token_delay_ms=0)
    contexto = "[[frag]] Los reembolsos tardan cinco dias habiles. [[/frag]]"
    mensajes = [ChatMessage("system", contexto), ChatMessage("user", "cuanto tardan?")]
    tokens = [t async for t in provider.stream_chat(mensajes)]
    assert len(tokens) > 3
    assert "reembolsos" in "".join(tokens).lower()


async def test_el_fake_sin_contexto_sugiere_escalar():
    provider = FakeProvider(token_delay_ms=0)
    tokens = [t async for t in provider.stream_chat([ChatMessage("user", "hola")])]
    assert "escalar" in "".join(tokens).lower()
