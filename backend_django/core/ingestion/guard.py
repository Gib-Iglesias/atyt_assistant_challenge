"""
Deteccion de intentos de inyeccion de prompt en el contenido ingerido.

No es un filtro de seguridad por si solo: el aislamiento real lo dan el JWT y la
capa de repositorios, que no permiten expresar una consulta a otro tenant. Esto
es defensa en profundidad y, sobre todo, visibilidad: marca el fragmento para
que operaciones lo vea en el admin y para degradar su peso en la recuperacion.

El contenido marcado se sigue indexando. Borrarlo daria una falsa sensacion de
seguridad y dejaria el sistema sin probar frente al siguiente documento
envenenado.
"""
from __future__ import annotations

import re
import unicodedata

# (patron compilado, motivo legible)
PATRONES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"nota interna del sistema", re.I), "se hace pasar por nota del sistema"),
    (re.compile(r"instrucci[oó]n(?:es)?\s+(?:prioritaria|del sistema|para el asistente)", re.I),
     "se autodenomina instruccion prioritaria"),
    (re.compile(r"ignor(?:a|ando|ar|e)\s+(?:las\s+|los\s+)?(?:restricciones|instrucciones|reglas|politicas)", re.I),
     "pide ignorar restricciones previas"),
    (re.compile(r"(?:consulta|incluye|muestra|accede)[^.]{0,60}(?:otros|dem[aá]s)\s+tenants", re.I),
     "pide acceder a datos de otros tenants"),
    (re.compile(r"(?:sin|omitiendo)\s+(?:las\s+)?restricciones\s+(?:previas|anteriores|de alcance)", re.I),
     "pide omitir el alcance por cliente"),
    (re.compile(r"prompt\s+del\s+sistema|system\s+prompt", re.I), "menciona el prompt del sistema"),
    (re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.I),
     "ignore previous instructions"),
    (re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above)", re.I), "disregard previous"),
    (re.compile(r"you\s+are\s+now\s+|act\s+as\s+(?:an?\s+)?(?:admin|system|developer)", re.I),
     "intenta reasignar el rol del asistente"),
    (re.compile(r"anular?\s+(?:las\s+)?(?:politicas|restricciones|reglas)", re.I),
     "pide anular politicas"),
]


def _normalizar(texto: str) -> str:
    """Quita acentos para que los patrones acierten con y sin tildes."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def analizar(texto: str) -> tuple[bool, str]:
    """
    Devuelve (es_sospechoso, motivo).

    El motivo se guarda en el chunk y se muestra en el admin de Django.
    """
    candidatos = (texto, _normalizar(texto))
    motivos: list[str] = []
    for patron, motivo in PATRONES:
        if any(patron.search(c) for c in candidatos):
            motivos.append(motivo)
    if not motivos:
        return False, ""
    # Sin duplicados y estable, para que el motivo sea reproducible.
    unicos = list(dict.fromkeys(motivos))
    return True, "; ".join(unicos)[:255]
