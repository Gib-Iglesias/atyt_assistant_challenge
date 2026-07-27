"""
Repositorios: la unica via de acceso a datos de negocio.

Cada funcion recibe el TenantContext y aplica el filtro por tenant en el propio
SQL. Ninguna acepta tenant_id como argumento suelto: el llamador no puede pedir
"los datos del tenant 7", solo "los datos de mi contexto". Es lo que hace que la
inyeccion del enunciado no tenga forma de expresarse.
"""
from __future__ import annotations

from typing import Any

from ..deps import TenantContext
from .engine import get_connection


def buscar_chunks(ctx: TenantContext, match_query: str, limite: int) -> list[dict[str, Any]]:
    """Busqueda BM25 sobre el indice FTS5, acotada al tenant del contexto."""
    if ctx.tenant_id is None:
        return []
    sql = """
        SELECT  c.id, c.document_id, c.page_start, c.page_end, c.text,
                c.is_suspicious, d.title, -bm25(chunk_fts) AS score
        FROM chunk_fts
        JOIN core_documentchunk c ON c.id = chunk_fts.rowid
        JOIN core_document d       ON d.id = c.document_id
        WHERE chunk_fts MATCH ? AND c.tenant_id = ?
        ORDER BY score DESC
        LIMIT ?;
    """
    with get_connection() as conn:
        filas = conn.execute(sql, (match_query, ctx.tenant_id, limite)).fetchall()
    return [dict(f) for f in filas]


def buscar_pedido(ctx: TenantContext, referencia: str) -> dict[str, Any] | None:
    """Un pedido por referencia. El filtro por tenant impide leer el de otro cliente."""
    if ctx.tenant_id is None:
        return None
    sql = """
        SELECT reference, customer_email, status, total_amount, currency, placed_at, notes
        FROM core_order
        WHERE tenant_id = ? AND reference = ?
        LIMIT 1;
    """
    with get_connection() as conn:
        fila = conn.execute(sql, (ctx.tenant_id, referencia.strip())).fetchone()
    return dict(fila) if fila else None


def historial_cliente(ctx: TenantContext, email: str, limite: int = 10) -> list[dict[str, Any]]:
    """Pedidos recientes de un cliente dentro del tenant del contexto."""
    if ctx.tenant_id is None:
        return []
    sql = """
        SELECT reference, status, total_amount, currency, placed_at
        FROM core_order
        WHERE tenant_id = ? AND customer_email = ?
        ORDER BY placed_at DESC
        LIMIT ?;
    """
    with get_connection() as conn:
        filas = conn.execute(sql, (ctx.tenant_id, email.strip().lower(), limite)).fetchall()
    return [dict(f) for f in filas]


def crear_ticket_escalado(ctx: TenantContext, asunto: str, cuerpo: str,
                          order_reference: str | None = None) -> int:
    """
    Crea un ticket en estado 'escalated'. Es la unica escritura de negocio del
    servicio de IA, y tambien va acotada al tenant del contexto.
    """
    if ctx.tenant_id is None:
        raise ValueError("No se puede escalar sin tenant.")
    with get_connection() as conn:
        order_id = None
        if order_reference:
            fila = conn.execute(
                "SELECT id FROM core_order WHERE tenant_id = ? AND reference = ? LIMIT 1;",
                (ctx.tenant_id, order_reference.strip()),
            ).fetchone()
            order_id = fila["id"] if fila else None
        cur = conn.execute(
            """
            INSERT INTO core_ticket
                (tenant_id, order_id, subject, body, resolution, status, priority, created_at)
            VALUES (?, ?, ?, ?, '', 'escalated', 'normal', datetime('now'));
            """,
            (ctx.tenant_id, order_id, asunto[:255], cuerpo),
        )
        return int(cur.lastrowid)
