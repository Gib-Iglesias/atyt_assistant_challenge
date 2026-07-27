"""
Prueba de extremo a extremo del endpoint /api/chat/stream con TestClient.

Verifica el flujo completo con el proveedor falso: token -> citations -> done, y
el camino de escalado cuando no hay material.
"""
import jwt
import pytest
from fastapi.testclient import TestClient


def _token(secret, tenant_id=1, slug="acme", agente=True):
    import time
    payload = {
        "sub": "1", "username": "agente_acme", "tenant_id": tenant_id, "tenant_slug": slug,
        "is_support_agent": agente, "is_staff": False, "iss": "atyt-assistant-django",
        "iat": int(time.time()), "exp": int(time.time()) + 600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def client(settings):
    from service_ai.main import app
    with TestClient(app) as c:
        yield c


def _eventos(texto: str) -> list[str]:
    return [l.removeprefix("event: ") for l in texto.splitlines() if l.startswith("event: ")]


def test_pregunta_con_respuesta_emite_tokens_y_citas(client):
    r = client.post(
        "/api/chat/stream",
        json={"message": "cuanto tardan los reembolsos?"},
        headers={"Authorization": f"Bearer {_token('test-secret')}"},
    )
    assert r.status_code == 200
    eventos = _eventos(r.text)
    assert "token" in eventos
    assert "citations" in eventos
    assert eventos[-1] == "done"


def test_pregunta_sin_material_escala(client):
    r = client.post(
        "/api/chat/stream",
        json={"message": "xyzzy qwerty termino inexistente zzz"},
        headers={"Authorization": f"Bearer {_token('test-secret')}"},
    )
    assert r.status_code == 200
    eventos = _eventos(r.text)
    assert "escalated" in eventos


def test_sin_token_devuelve_401(client):
    r = client.post("/api/chat/stream", json={"message": "hola"})
    assert r.status_code == 401


def test_token_de_otro_secreto_devuelve_401(client):
    r = client.post(
        "/api/chat/stream",
        json={"message": "hola"},
        headers={"Authorization": f"Bearer {_token('secreto-equivocado')}"},
    )
    assert r.status_code == 401


def test_health_reporta_proveedor(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["llm_provider"] == "fake"
    assert body["waiting"] == 0
