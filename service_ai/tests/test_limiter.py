import asyncio

import pytest

from service_ai.llm.limiter import CapacityError, ConcurrencyLimiter


async def test_no_deja_pasar_mas_del_maximo_a_la_vez():
    limiter = ConcurrencyLimiter(max_concurrency=2, queue_max_size=100, queue_timeout_s=5)
    activos = 0
    pico = 0

    async def tarea():
        nonlocal activos, pico
        async with limiter.slot():
            activos += 1
            pico = max(pico, activos)
            await asyncio.sleep(0.02)
            activos -= 1

    await asyncio.gather(*[tarea() for _ in range(10)])
    assert pico <= 2


async def test_rechaza_cuando_la_cola_esta_llena():
    limiter = ConcurrencyLimiter(max_concurrency=1, queue_max_size=1, queue_timeout_s=2)

    async def ocupa():
        async with limiter.slot():
            await asyncio.sleep(0.2)

    # Uno ocupa el slot, otro espera en cola (la llena), el tercero debe rebotar.
    t1 = asyncio.create_task(ocupa())
    await asyncio.sleep(0.02)
    t2 = asyncio.create_task(ocupa())
    await asyncio.sleep(0.02)
    with pytest.raises(CapacityError):
        async with limiter.slot():
            pass
    await asyncio.gather(t1, t2)
