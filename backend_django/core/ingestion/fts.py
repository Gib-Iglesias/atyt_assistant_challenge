"""
Indice de texto completo.

Se usa FTS5, que viene compilado dentro de SQLite: no es un servicio aparte y no
contradice la restriccion de no levantar infraestructura adicional. Ver
docs/DECISIONES.md, seccion 5.

La tabla es de contenido externo (content='core_documentchunk'), asi que no
duplica el texto: guarda solo el indice invertido y lee los valores de la tabla
real. Se reconstruye entera despues de cada ingesta, que para el volumen del MVP
es mas simple y mas seguro que mantener triggers de sincronizacion.

No vive en una migracion a proposito: las migraciones deben poder aplicarse
sobre Postgres o MySQL, donde esto se sustituye por tsvector + GIN.
"""
from __future__ import annotations

from django.db import connection

TABLA = "chunk_fts"
TABLA_ORIGEN = "core_documentchunk"

DDL = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS {TABLA} USING fts5(
    text,
    content='{TABLA_ORIGEN}',
    content_rowid='id',
    tokenize="unicode61 remove_diacritics 2"
);
"""


def soportado() -> bool:
    """FTS5 solo aplica en SQLite. En otros motores el indice se resuelve distinto."""
    return connection.vendor == "sqlite"


def crear_indice() -> None:
    if not soportado():
        return
    with connection.cursor() as cur:
        cur.execute(DDL)


def reconstruir() -> int:
    """Regenera el indice completo desde la tabla de chunks. Devuelve filas indexadas."""
    if not soportado():
        return 0
    crear_indice()
    with connection.cursor() as cur:
        cur.execute(f"INSERT INTO {TABLA}({TABLA}) VALUES('rebuild');")
        cur.execute(f"SELECT count(*) FROM {TABLA};")
        return cur.fetchone()[0]


def eliminar_indice() -> None:
    if not soportado():
        return
    with connection.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TABLA};")


def buscar(consulta: str, tenant_id: int, limite: int = 6) -> list[dict]:
    """
    Busqueda BM25 acotada a un tenant.

    El filtro por tenant va en el SQL, no en el prompt. Es la misma consulta que
    usara el servicio de IA en modo lectura. bm25() devuelve valores negativos y
    mas bajo significa mejor coincidencia; se invierte el signo para que un
    numero mayor sea mejor y el umbral se lea de forma natural.
    """
    if not soportado():
        return []
    sql = f"""
        SELECT  c.id, c.document_id, c.page_start, c.page_end, c.text,
                c.is_suspicious, d.title, -bm25({TABLA}) AS score
        FROM {TABLA}
        JOIN {TABLA_ORIGEN} c ON c.id = {TABLA}.rowid
        JOIN core_document d  ON d.id = c.document_id
        WHERE {TABLA} MATCH %s AND c.tenant_id = %s
        ORDER BY score DESC
        LIMIT %s;
    """
    with connection.cursor() as cur:
        cur.execute(sql, [consulta, tenant_id, limite])
        columnas = [col[0] for col in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def preparar_consulta(texto: str) -> str:
    """
    Convierte lenguaje natural en una consulta MATCH valida.

    FTS5 interpreta comillas, parentesis y operadores; una pregunta escrita por
    una persona los rompe. Se extraen los terminos utiles y se unen con OR para
    que BM25 ordene, en lugar de exigir que aparezcan todos.
    """
    import re

    VACIAS = {
        "que", "cual", "cuales", "como", "cuando", "donde", "quien", "para", "por",
        "con", "sin", "los", "las", "una", "uno", "del", "the", "and", "mi", "me",
        "es", "son", "esta", "estan", "hay", "tiene", "puedo", "puede", "sobre",
    }
    tokens = [t for t in re.findall(r"\w+", texto.lower(), flags=re.UNICODE) if len(t) > 2]
    tokens = [t for t in tokens if t not in VACIAS]
    if not tokens:
        tokens = re.findall(r"\w+", texto.lower())[:4]
    unicos = list(dict.fromkeys(tokens))[:12]
    return " OR ".join(f'"{t}"' for t in unicos)
