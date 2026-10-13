from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence

@dataclass(frozen=True)
class Action:
    equipment: str
    action: str
    hours: float
    window: Sequence[str] = field(default_factory=list)


def calcular_ahorro_potencial(
    potencia_kw: float,
    horas: float,
    precio_clp_kwh: float,
) -> float:

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

    return calcular_ahorro_potencial(potencia_kw, action.hours, precio_clp_kwh)
