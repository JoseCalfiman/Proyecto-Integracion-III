"""Ventana deslizante de temperaturas por cámara.

Reglas:
- Se conserva como máximo `ventana_minutos` de historia, medidos contra el
  timestamp de la lectura más reciente (no contra el reloj del servidor).
- El `maxlen` del deque pone el tope de mediciones.
- Una lectura con timestamp igual o anterior a la última se ignora (duplicados
  o mensajes desordenados).
- Si un timestamp retrocede más que la ventana completa (reloj del sensor
  reiniciado), se descarta la historia y se parte de cero.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta


def actualizar_ventana(
    buffer: deque,
    timestamp: datetime,
    temperature: float,
    ventana_minutos: float,
) -> bool:
    """Agrega una lectura a la ventana. Devuelve False si fue ignorada."""
    ventana = timedelta(minutes=ventana_minutos)

    if buffer:
        ultimo = buffer[-1]["timestamp"]
        if timestamp <= ultimo:
            if ultimo - timestamp > ventana:
                buffer.clear()
            else:
                return False

    buffer.append({"timestamp": timestamp, "temperature": temperature})

    limite_inferior = timestamp - ventana
    while buffer and buffer[0]["timestamp"] < limite_inferior:
        buffer.popleft()

    return True
