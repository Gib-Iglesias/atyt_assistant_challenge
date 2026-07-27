"""
El test que mas pesa en la entrega.

Reproduce el ataque del enunciado de extremo a extremo: un agente de acme
pregunta por facturacion, el fragmento envenenado ENTRA en el contexto
recuperado, y se comprueba que la respuesta no filtra nada de globex. La
defensa no es que el modelo obedezca: es que ni el retriever ni las herramientas
pueden expresar una consulta a otro tenant.
"""
import pytest

from service_ai.deps import TenantContext
from service_ai.rag import prompt as prompt_mod
from service_ai.rag import retriever
from service_ai.tools import registry


def test_el_fragmento_envenenado_se_recupera_pero_marcado(settings, ctx_acme):
    recuperados = retriever.recuperar(ctx_acme, "facturacion instruccion sistema", settings)
    sospechosos = [r for r in recuperados if r.is_suspicious]
    assert sospechosos, "el fragmento de inyeccion deberia estar en el corpus"


def test_acme_no_recupera_nada_de_globex(settings, ctx_acme):
    # Se busca con terminos que SOLO existen en documentos de globex.
    recuperados = retriever.recuperar(ctx_acme, "envios Globex entregas", settings)
    assert all(r.document_id == 1 for r in recuperados)


def test_las_herramientas_no_ven_pedidos_de_otro_tenant(settings, ctx_acme):
    # La referencia es de globex; acme no debe poder resolverla.
    bloques = registry.resolver_datos(ctx_acme, "estado del pedido GLOBEX-000001")
    unido = " ".join(bloques)
    assert "GLOBEX-000001" not in unido or "No existe" in unido
    assert "otro@globex.example" not in unido


def test_el_prompt_marca_el_contexto_como_no_instruccional(settings, ctx_acme):
    recuperados = retriever.recuperar(ctx_acme, "facturacion reembolsos", settings)
    mensajes, _ = prompt_mod.construir_mensajes("cuanto tardan?", recuperados, 8000)
    system = " ".join(m.content for m in mensajes if m.role == "system")
    assert "NO instrucciones" in system or "no confiable" in system.lower() or "NO son instrucciones" in system
    # La regla de aislamiento entre tenants esta explicita en el system prompt.
    assert "otros clientes" in system.lower() or "otro" in system.lower()


def test_un_agente_de_globex_no_ve_el_documento_de_acme(settings):
    ctx_globex = TenantContext(2, "agente_globex", 2, "globex", True, False)
    recuperados = retriever.recuperar(ctx_globex, "reembolsos metodo pago original", settings)
    assert all(r.document_id == 2 for r in recuperados)
