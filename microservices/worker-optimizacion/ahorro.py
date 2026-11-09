from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence


EQUIPMENT_NAMES = {
    "camaras_2_y_3": "Cámaras 2 y 3",
    "eq_climatizacion_zona_b": "Climatización zona B",
}

ACTION_NAMES = {
    "apagar": "Apagar",
    "reducir_carga": "Reducir carga en",
    "encender": "Encender",
    "mantener": "Mantener en operación",
}


@dataclass(frozen=True)
class Action:
    equipment: str
    action: str
    hours: float
    window: Sequence[str] = field(default_factory=list)


def es_recomendacion_util(
    monto: object,
    porcentaje: object,
    rationale: object = None,
) -> bool:
    """Indica si una recomendación aporta ahorro o tiene una razón explícita."""
    try:
        monto_num = float(monto) if monto is not None else math.nan
        porcentaje_num = float(porcentaje) if porcentaje is not None else math.nan
    except (TypeError, ValueError):
        monto_num = porcentaje_num = math.nan

    if (
        math.isfinite(monto_num)
        and math.isfinite(porcentaje_num)
        and monto_num > 0
        and porcentaje_num > 0
    ):
        return True

    if not isinstance(rationale, str):
        return False
    cleaned_rationale = rationale.strip().casefold()
    return (
        any(character.isalpha() for character in cleaned_rationale)
        and cleaned_rationale
        not in {
            "",
            "n/a",
            "na",
            "null",
            "none",
            "sin justificación",
            "sin justificacion",
        }
    )


def generar_textos_recomendacion(
    accion: str,
    equipo: str,
    horas: float,
    ventana: Sequence[str],
    monto: float,
    porcentaje: float,
) -> tuple[str, str]:
    """Construye un título y una justificación legibles para el usuario."""
    equipo_label = EQUIPMENT_NAMES.get(
        equipo,
        equipo.replace("_", " ").strip().capitalize() or "equipo",
    )
    accion_label = ACTION_NAMES.get(
        accion,
        accion.replace("_", " ").strip().capitalize() or "Optimizar",
    )
    titulo = f"{accion_label} {equipo_label}"

    duracion = f"{horas:g} hora" if horas == 1 else f"{horas:g} horas"
    detalle_ventana = ""
    if len(ventana) == 2:
        detalle_ventana = f" en el horario de {ventana[0]} a {ventana[1]}"

    monto_formateado = f"${monto:,.0f}".replace(",", ".")
    porcentaje_formateado = f"{porcentaje:.2f}".replace(".", ",")
    rationale = (
        f"{titulo} durante {duracion}{detalle_ventana}. Ahorro estimado: "
        f"{monto_formateado} CLP ({porcentaje_formateado}% del costo diario "
        "proyectado)."
    )
    return titulo, rationale


def calcular_ahorro_potencial(
    potencia_kw: float,
    horas: float,
    precio_clp_kwh: float,
) -> float:

    if not math.isfinite(potencia_kw) or potencia_kw < 0:
        raise ValueError("potencia_kw debe ser mayor o igual a 0")
    if not math.isfinite(horas) or horas < 0:
        raise ValueError("horas debe ser mayor o igual a 0")
    if not math.isfinite(precio_clp_kwh) or precio_clp_kwh < 0:
        raise ValueError("precio_clp_kwh debe ser mayor o igual a 0")
    return potencia_kw * horas * precio_clp_kwh


def calcular_ahorro_action(
    action: Action,
    potencia_kw: float,
    precio_clp_kwh: float,
) -> float:

    return calcular_ahorro_potencial(potencia_kw, action.hours, precio_clp_kwh)
