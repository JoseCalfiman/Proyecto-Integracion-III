"""Módulo de validación de reglas HACCP para cámaras frigoríficas.

Este módulo encapsula la lógica de control de temperatura y tiempo para
identificar alertas por riesgo de cadena de frío.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

DEFAULT_HACCP_RULE = {
    "name": "cold_chain_temperature",
    "max_temp_c": 4.0,
    "warning_duration_seconds": 120,
    "critical_duration_seconds": 300,
    "critical_temp_c": 6.0,
    "sample_interval_seconds": 10,
}


def _normalize_rule(rule: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Devuelve una regla HACCP final con valores por defecto."""
    normalized = DEFAULT_HACCP_RULE.copy()
    if rule:
        normalized.update(rule)
    return normalized


def evaluate_temperature_rule(
    temperature_c: float,
    duration_seconds: float,
    rule: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Evalúa una medición puntual y su duración de exposición.

    Regla base: si la temperatura supera los 4 °C durante más de 120 segundos,
    se considera una alerta HACCP.
    """
    active_rule = _normalize_rule(rule)
    max_temp = float(active_rule["max_temp_c"])
    warning_seconds = float(active_rule["warning_duration_seconds"])
    critical_seconds = float(active_rule["critical_duration_seconds"])
    critical_temp = float(active_rule.get("critical_temp_c", max_temp))

    is_over_limit = float(temperature_c) > max_temp
    is_alert = is_over_limit and float(duration_seconds) >= warning_seconds

    if is_alert:
        if float(temperature_c) >= critical_temp or float(duration_seconds) >= critical_seconds:
            severity = "critical"
        else:
            severity = "warning"
        message = (
            f"Alerta HACCP: temperatura {temperature_c}°C supera el límite de "
            f"{max_temp}°C durante {duration_seconds} segundos."
        )
    elif is_over_limit:
        severity = "warning"
        message = (
            f"Temperatura fuera de rango: {temperature_c}°C, pero aún no supera "
            f"el tiempo mínimo de alerta ({warning_seconds} s)."
        )
    else:
        severity = "normal"
        message = (
            f"Temperatura normal: {temperature_c}°C dentro del límite de "
            f"{max_temp}°C."
        )

    return {
        "is_alert": is_alert,
        "severity": severity,
        "temperature_c": float(temperature_c),
        "duration_seconds": float(duration_seconds),
        "threshold_c": max_temp,
        "rule": active_rule,
        "message": message,
    }


def evaluate_temperature_series(
    temperatures: Iterable[float],
    sample_interval_seconds: int = 10,
    rule: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Evalúa una serie temporal de lecturas para detectar violaciones HACCP.

    La lógica asume que cada valor representa una muestra con un intervalo fijo.
    Para una secuencia continua por encima del límite, se calcula el tiempo total
    de violación multiplicando la cantidad de muestras por el intervalo.
    """
    active_rule = _normalize_rule(rule)
    max_temp = float(active_rule["max_temp_c"])
    warning_seconds = float(active_rule["warning_duration_seconds"])
    sample_interval = int(sample_interval_seconds or active_rule.get("sample_interval_seconds", 10))

    values = [float(item) for item in temperatures]
    if not values:
        return {
            "has_violation": False,
            "total_violation_seconds": 0,
            "severity": "normal",
            "rule": active_rule,
            "violations": [],
            "message": "No hay lecturas para evaluar.",
        }

    violating_runs: List[dict[str, Any]] = []
    current_run: List[float] = []

    for value in values:
        if value > max_temp:
            current_run.append(value)
        elif current_run:
            run_duration = (len(current_run) + 1) * sample_interval
            violating_runs.append(
                {
                    "start_index": len(violating_runs),
                    "length": len(current_run),
                    "duration_seconds": run_duration,
                    "max_temp_c": max(current_run),
                }
            )
            current_run = []

    if current_run:
        run_duration = (len(current_run) + 1) * sample_interval
        violating_runs.append(
            {
                "start_index": len(violating_runs),
                "length": len(current_run),
                "duration_seconds": run_duration,
                "max_temp_c": max(current_run),
            }
        )

    total_violation_seconds = sum(item["duration_seconds"] for item in violating_runs)
    has_violation = total_violation_seconds >= warning_seconds

    if has_violation:
        severity = "critical" if total_violation_seconds >= float(active_rule["critical_duration_seconds"]) else "warning"
        message = (
            f"Se detectó una violación HACCP: {total_violation_seconds} segundos "
            f"por encima de {max_temp}°C."
        )
    else:
        severity = "normal"
        message = (
            f"La serie está dentro del rango aceptable: máximo {max(values)}°C "
            f"y ninguna ventana supera {warning_seconds} segundos."
        )

    return {
        "has_violation": has_violation,
        "total_violation_seconds": total_violation_seconds,
        "severity": severity,
        "rule": active_rule,
        "violations": violating_runs,
        "message": message,
    }


__all__ = [
    "DEFAULT_HACCP_RULE",
    "evaluate_temperature_rule",
    "evaluate_temperature_series",
]
