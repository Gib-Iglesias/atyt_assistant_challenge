"""
Serializacion de eventos Server-Sent Events.

Se emiten eventos tipados en lugar de texto plano, porque las citas solo pueden
adjuntarse cuando la respuesta esta completa y el escalado necesita su propio
evento. Formato: 'event: <tipo>' + 'data: <json>'.
"""
from __future__ import annotations

import json
from typing import Any


def evento(tipo: str, data: Any) -> str:
    return f"event: {tipo}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
