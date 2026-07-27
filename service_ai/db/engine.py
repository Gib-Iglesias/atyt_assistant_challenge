"""
Acceso de solo lectura a la base que gobierna Django.

El servicio de IA nunca migra ni altera el esquema; lee pedidos, tickets y
chunks, y escribe unicamente en las tablas de conversacion y en tickets al
escalar. Se usa sqlite3 de la libreria estandar con la misma configuracion WAL
que aplica Django, para no reintroducir dependencias.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from ..config import get_settings


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    path = settings.sqlite_path
    if path is None:
        raise RuntimeError(
            "El servicio de IA de este MVP solo soporta SQLite. "
            "Para Postgres, sustituir db/engine.py por un pool adecuado."
        )
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
