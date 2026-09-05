"""Cálculo de ahorro potencial (entregable).

Aplica una acción específica sobre un equipo (por ejemplo, "apagar el
compresor 2h en horario punta"), calcula la reducción de consumo en kWh
y la multiplica por el precio del kWh (``precio_clp_kwh``) para obtener
el ahorro estimado en CLP.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class Action:
    """Acción específica de optimización sobre un equipo.

    Attributes:
        equipment: Nombre o identificador del equipo.
        action: Tipo de acción (por ejemplo, ``"apagar"``,
            ``"reducir_carga"``).
        hours: Horas de aplicación de la acción (por ejemplo, ``2``).
        window: Ventana horaria en que se aplica, por ejemplo
            ``["18:00", "22:00"]``.
    """

    equipment: str
    action: str
    hours: float
    window: Sequence[str] = field(default_factory=list)


def calcular_ahorro_potencial(
    potencia_kw: float,
    horas: float,
    precio_clp_kwh: float,
) -> float:
    """Calcula el ahorro en CLP de reducir el consumo durante un periodo.

    Args:
        potencia_kw: Potencia nominal o consumo del equipo en kW.
        horas: Horas en que se aplica la acción (por ejemplo, apagado).
        precio_clp_kwh: Precio del kWh en CLP (``precio_clp_kwh``).

    Returns:
        Ahorro estimado en CLP (``potencia_kw * horas * precio_clp_kwh``).
    """
    if potencia_kw < 0:
        raise ValueError("potencia_kw debe ser mayor o igual a 0")
    if horas < 0:
        raise ValueError("horas debe ser mayor o igual a 0")
    if precio_clp_kwh < 0:
        raise ValueError("precio_clp_kwh debe ser mayor o igual a 0")
    return potencia_kw * horas * precio_clp_kwh


def calcular_ahorro_action(
    action: Action,
    potencia_kw: float,
    precio_clp_kwh: float,
) -> float:
    """Aplica una :class:`Action` y devuelve el ahorro estimado en CLP.

    Args:
        action: Acción específica (equipo, tipo, horas y ventana).
        potencia_kw: Potencia nominal o consumo del equipo en kW.
        precio_clp_kwh: Precio del kWh en CLP (``precio_clp_kwh``).

    Returns:
        Ahorro estimado en CLP.
    """
    return calcular_ahorro_potencial(potencia_kw, action.hours, precio_clp_kwh)
