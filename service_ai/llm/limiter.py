"""
Limite global de concurrencia contra el proveedor de LLM.

El enunciado fija 20 peticiones concurrentes para toda la cuenta. Se implementa
con un asyncio.Semaphore, que solo es un limite real con un unico worker de
uvicorn; por eso el servicio corre con --workers 1. La alternativa multi-worker
(arriendo en SQLite) esta descrita y descartada en docs/DECISIONES.md, seccion 4.

Ademas del semaforo hay una cola acotada: si entran mas peticiones de las que
caben, esperan hasta un tope; superado, se rechaza rapido en vez de acumular
conexiones colgadas.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager


class CapacityError(RuntimeError):
    """La cola de espera al proveedor esta llena."""


class ConcurrencyLimiter:
    def __init__(self, max_concurrency: int, queue_max_size: int, queue_timeout_s: float) -> None:
        self._sem = asyncio.Semaphore(max_concurrency)
        self._max_concurrency = max_concurrency
        self._queue_max_size = queue_max_size
        self._queue_timeout = queue_timeout_s
        self._esperando = 0
        self._lock = asyncio.Lock()

    @property
    def en_espera(self) -> int:
        return self._esperando

    @asynccontextmanager
    async def slot(self):
        async with self._lock:
            if self._esperando >= self._queue_max_size:
                raise CapacityError("El servicio esta saturado. Intentalo de nuevo en unos segundos.")
            self._esperando += 1
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=self._queue_timeout)
        except asyncio.TimeoutError as exc:
            raise CapacityError("Tiempo de espera agotado ante el proveedor de IA.") from exc
        finally:
            async with self._lock:
                self._esperando -= 1
        try:
            yield
        finally:
            self._sem.release()
