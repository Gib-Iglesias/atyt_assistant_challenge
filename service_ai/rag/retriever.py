"""
Recuperacion (lado lectura). Traduce la pregunta a una consulta FTS5, busca los
mejores fragmentos del tenant y decide si hay material suficiente para responder.

El chunking, el indexado y la deteccion de inyeccion viven en Django (escritura).
Aqui solo se lee. Ver docs/DECISIONES.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import Settings
from ..db import repositories
from ..deps import TenantContext

VACIAS = {
    "que", "cual", "cuales", "como", "cuando", "donde", "quien", "para", "por",
    "con", "sin", "los", "las", "una", "uno", "del", "the", "and", "mi", "me",
    "es", "son", "esta", "estan", "hay", "tiene", "puedo", "puede", "sobre", "mis",
}
# Expansion corta de sinonimos del dominio: mitiga que BM25 no entienda parafrasis.
SINONIMOS = {
    "devolver": ["reembolso", "devolucion"], "devuelven": ["reembolso", "devolucion"],
    "dinero": ["reembolso", "importe"], "factura": ["facturacion"],
    "envio": ["entrega", "logistica"], "tarda": ["plazo", "dias"],
}


@dataclass(frozen=True)
class Recuperado:
    chunk_id: int
    document_id: int
    title: str
    page_start: int
    page_end: int
    text: str
    score: float
    is_suspicious: bool


def preparar_match(texto: str) -> str:
    tokens = [t for t in re.findall(r"\w+", texto.lower(), flags=re.UNICODE) if len(t) > 2]
    utiles = [t for t in tokens if t not in VACIAS]
    expandido: list[str] = []
    for t in (utiles or tokens[:4]):
        expandido.append(t)
        expandido.extend(SINONIMOS.get(t, []))
    unicos = list(dict.fromkeys(expandido))[:12]
    return " OR ".join(f'"{t}"' for t in unicos) if unicos else '""'


def recuperar(ctx: TenantContext, pregunta: str, settings: Settings) -> list[Recuperado]:
    match = preparar_match(pregunta)
    if match == '""':
        return []
    filas = repositories.buscar_chunks(ctx, match, settings.retrieval_top_k)
    return [
        Recuperado(
            chunk_id=f["id"], document_id=f["document_id"], title=f["title"],
            page_start=f["page_start"], page_end=f["page_end"], text=f["text"],
            score=float(f["score"]), is_suspicious=bool(f["is_suspicious"]),
        )
        for f in filas
    ]


def hay_material_suficiente(recuperados: list[Recuperado], settings: Settings) -> bool:
    """Regla de escalado por recuperacion: sin ningun fragmento sobre el umbral, no se responde."""
    return any(r.score >= settings.retrieval_min_score for r in recuperados)
