"""Escalado: sin material suficiente se crea un ticket en estado escalated."""
import sqlite3

from service_ai.tools import tickets


def test_escalar_crea_ticket_del_tenant(settings, ctx_acme, db):
    ticket_id = tickets.escalar(ctx_acme, "una pregunta imposible de responder")
    conn = sqlite3.connect(db)
    fila = conn.execute(
        "SELECT tenant_id, status, priority FROM core_ticket WHERE id = ?", (ticket_id,)
    ).fetchone()
    conn.close()
    assert fila == (1, "escalated", "normal")


def test_escalar_asocia_el_pedido_si_la_referencia_existe(settings, ctx_acme, db):
    ticket_id = tickets.escalar(ctx_acme, "problema con ACME-000001", "ACME-000001")
    conn = sqlite3.connect(db)
    order_id = conn.execute(
        "SELECT order_id FROM core_ticket WHERE id = ?", (ticket_id,)
    ).fetchone()[0]
    conn.close()
    assert order_id == 1


def test_no_asocia_pedido_de_otro_tenant(settings, ctx_acme, db):
    # GLOBEX-000001 no es de acme: el ticket se crea sin pedido asociado.
    ticket_id = tickets.escalar(ctx_acme, "problema", "GLOBEX-000001")
    conn = sqlite3.connect(db)
    order_id = conn.execute(
        "SELECT order_id FROM core_ticket WHERE id = ?", (ticket_id,)
    ).fetchone()[0]
    conn.close()
    assert order_id is None
