from service_ai.rag import retriever


def test_prepara_una_consulta_match_valida():
    q = retriever.preparar_match("cuanto tardan los reembolsos?")
    assert "OR" in q and "reembolsos" in q


def test_expande_sinonimos_del_dominio():
    q = retriever.preparar_match("me devuelven el dinero?")
    assert "reembolso" in q  # 'devuelven' y 'dinero' expanden a 'reembolso'


def test_recupera_solo_del_tenant(settings, ctx_acme, ctx_globex):
    r_acme = retriever.recuperar(ctx_acme, "reembolsos", settings)
    r_globex = retriever.recuperar(ctx_globex, "reembolsos", settings)
    assert all(x.document_id == 1 for x in r_acme)
    assert all(x.document_id == 2 for x in r_globex)


def test_umbral_de_material_suficiente(settings, ctx_acme):
    recuperados = retriever.recuperar(ctx_acme, "reembolsos metodo de pago", settings)
    assert retriever.hay_material_suficiente(recuperados, settings)

    vacio = retriever.recuperar(ctx_acme, "xyzzy termino inexistente qwerty", settings)
    assert not retriever.hay_material_suficiente(vacio, settings)
