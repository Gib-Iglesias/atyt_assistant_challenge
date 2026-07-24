"""
Generacion de los PDF sinteticos del corpus de ejemplo.

Se usa el canvas de bajo nivel de reportlab en lugar de platypus porque permite
controlar el numero exacto de paginas: el enunciado pide documentos que lleguen
a las 400 paginas, y necesitamos alcanzarlo sin construir el documento varias
veces para medirlo.
"""
from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path
from typing import Iterable, Iterator

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

MARGEN = 20 * mm
INTERLINEA = 12
ANCHO_TEXTO = 92          # caracteres por linea
FUENTE, TAM = "Helvetica", 9.5
FUENTE_H, TAM_H = "Helvetica-Bold", 11


def _lineas(bloques: Iterator[tuple[str, str]], max_lineas: int) -> Iterator[list[tuple[str, str]]]:
    """Agrupa (tipo, texto) en paginas de como mucho max_lineas lineas."""
    pagina: list[tuple[str, str]] = []
    for tipo, texto in bloques:
        envuelto = textwrap.wrap(texto, width=ANCHO_TEXTO) or [""]
        trozo = [(tipo, linea) for linea in envuelto] + [("", "")]
        for linea in trozo:
            pagina.append(linea)
            if len(pagina) >= max_lineas:
                yield pagina
                pagina = []
    if pagina:
        yield pagina


def build_pdf(
    destino: Path,
    titulo: str,
    bloques: Iterator[tuple[str, str]],
    paginas_objetivo: int,
) -> tuple[int, str]:
    """
    Escribe el PDF y devuelve (numero_de_paginas, sha256).

    `bloques` puede ser un generador infinito: se corta al alcanzar
    `paginas_objetivo`.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(destino), pagesize=A4)
    ancho, alto = A4
    y_inicial = alto - 28 * mm
    max_lineas = int((y_inicial - MARGEN) / INTERLINEA)

    n = 0
    for pagina in _lineas(bloques, max_lineas):
        n += 1
        c.setFont(FUENTE_H, 8)
        c.drawString(MARGEN, alto - 15 * mm, titulo)
        c.setFont(FUENTE, 7.5)
        c.drawRightString(ancho - MARGEN, alto - 15 * mm, f"pag. {n}")
        c.line(MARGEN, alto - 17 * mm, ancho - MARGEN, alto - 17 * mm)

        y = y_inicial
        for tipo, linea in pagina:
            if tipo == "h":
                c.setFont(FUENTE_H, TAM_H)
            else:
                c.setFont(FUENTE, TAM)
            if linea:
                c.drawString(MARGEN, y, linea)
            y -= INTERLINEA
        c.showPage()
        if n >= paginas_objetivo:
            break

    c.save()
    digest = hashlib.sha256(destino.read_bytes()).hexdigest()
    return n, digest


def _quitar_repetidos(paginas: list[str]) -> list[str]:
    """
    Elimina encabezados y pies que se repiten en casi todas las paginas.

    Sin esto, el titulo del documento aparece dentro de cada fragmento y BM25
    puntua igual de alto todas las paginas del mismo documento, que es justo lo
    contrario de lo que necesita una cita util. La heuristica es generica y
    tambien sirve para los PDF reales del cliente, no solo para los sinteticos.
    """
    import re

    if len(paginas) < 2:
        return paginas

    # El numero de pagina suele ir en la misma linea que el encabezado, asi que
    # se normaliza antes de contar repeticiones; si no, ninguna linea coincide.
    marca_pagina = re.compile(r"\s*(pag\.|pagina|page)\s*\d+\s*$", re.I)
    solo_numero = re.compile(r"^\s*(pag\.|pagina|page)\s*\d+\s*$", re.I)

    def clave(linea: str) -> str:
        return marca_pagina.sub("", linea.strip()).strip()

    umbral = max(2, int(len(paginas) * 0.6))
    primeras: dict[str, int] = {}
    for texto in paginas:
        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
        if lineas:
            k = clave(lineas[0])
            if k:
                primeras[k] = primeras.get(k, 0) + 1
    repetidas = {linea for linea, veces in primeras.items() if veces >= umbral}

    limpias: list[str] = []
    for texto in paginas:
        lineas = [l for l in texto.splitlines() if l.strip()]
        if lineas and clave(lineas[0]) in repetidas:
            lineas = lineas[1:]
        lineas = [l for l in lineas if not solo_numero.match(l)]
        limpias.append("\n".join(lineas).strip())
    return limpias


def extraer_paginas(ruta: Path) -> list[str]:
    """Devuelve el texto de cada pagina. Importa pypdf aqui para no cargarlo al arrancar."""
    from pypdf import PdfReader

    reader = PdfReader(str(ruta))
    crudas = [(p.extract_text() or "").strip() for p in reader.pages]
    return _quitar_repetidos(crudas)
