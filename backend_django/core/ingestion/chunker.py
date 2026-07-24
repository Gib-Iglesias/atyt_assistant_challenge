"""
Fragmentacion del texto extraido de los PDF.

Regla que manda sobre todas las demas: un chunk nunca cruza el limite de una
pagina. Es lo que permite que la cita diga "documento X, pagina 37" en lugar de
apuntar a un rango difuso. El coste es que las paginas cortas producen chunks
cortos, algo asumible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SEPARADOR_PARRAFO = re.compile(r"\n\s*\n+")
ESPACIOS = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class Fragmento:
    ordinal: int
    text: str
    page_start: int
    page_end: int

    @property
    def char_count(self) -> int:
        return len(self.text)


def _limpiar(texto: str) -> str:
    texto = texto.replace("\r", "")
    texto = ESPACIOS.sub(" ", texto)
    return texto.strip()


def _trocear_pagina(texto: str, tam: int, solape: int) -> list[str]:
    """Corta el texto de una pagina en ventanas, respetando limites de parrafo."""
    texto = _limpiar(texto)
    if not texto:
        return []
    if len(texto) <= tam:
        return [texto]

    parrafos = [p.strip() for p in SEPARADOR_PARRAFO.split(texto) if p.strip()]
    if not parrafos:
        parrafos = [texto]

    trozos: list[str] = []
    actual = ""
    for parrafo in parrafos:
        if not actual:
            actual = parrafo
        elif len(actual) + 1 + len(parrafo) <= tam:
            actual = f"{actual}\n{parrafo}"
        else:
            trozos.append(actual)
            # Solape hacia atras: arrastra la cola del trozo anterior para no
            # partir una frase justo en la frontera.
            cola = actual[-solape:] if solape else ""
            actual = f"{cola}\n{parrafo}".strip() if cola else parrafo
    if actual:
        trozos.append(actual)

    # Un parrafo mas largo que la ventana se parte por longitud.
    finales: list[str] = []
    for trozo in trozos:
        if len(trozo) <= tam * 1.5:
            finales.append(trozo)
            continue
        paso = max(1, tam - solape)
        for i in range(0, len(trozo), paso):
            pedazo = trozo[i : i + tam].strip()
            if pedazo:
                finales.append(pedazo)
    return finales


def trocear_documento(
    paginas: list[str], tam: int = 900, solape: int = 150
) -> list[Fragmento]:
    """
    Convierte una lista de textos por pagina en fragmentos numerados.

    Las paginas se numeran desde 1, como las ve una persona al abrir el PDF.
    """
    fragmentos: list[Fragmento] = []
    ordinal = 0
    for indice, texto_pagina in enumerate(paginas, start=1):
        for trozo in _trocear_pagina(texto_pagina, tam=tam, solape=solape):
            fragmentos.append(
                Fragmento(ordinal=ordinal, text=trozo, page_start=indice, page_end=indice)
            )
            ordinal += 1
    return fragmentos
