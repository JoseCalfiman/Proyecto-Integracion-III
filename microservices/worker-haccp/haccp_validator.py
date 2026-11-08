"""Módulo de validación de reglas HACCP para cámaras frigoríficas.

Este módulo encapsula la lógica de control de temperatura y tiempo para
identificar alertas por riesgo de cadena de frío.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Iterable, List, Mapping, Optional

DEFAULT_HACCP_RULE = {
    "name": "cold_chain_temperature",
    "max_temp_c": 4.0,
    "min_temp_c": -30.0,
    "warning_duration_seconds": 900,
    "critical_duration_seconds": 1800,
    "critical_temp_c": 6.0,
    "sample_interval_seconds": 10,
}


class HaccpRuleConfigurationError(ValueError):
    """An active HACCP rule contains missing or incompatible values."""


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

    Se genera una alerta si la temperatura sale del rango permitido durante
    el tiempo de tolerancia configurado.
    """
    active_rule = _normalize_rule(rule)
    max_temp = float(active_rule["max_temp_c"])
    warning_seconds = float(active_rule["warning_duration_seconds"])
    critical_seconds = float(active_rule["critical_duration_seconds"])
    critical_temp = float(active_rule.get("critical_temp_c", max_temp))

    min_temp = float(active_rule.get("min_temp_c", float("-inf")))
    temperature = float(temperature_c)
    duration = float(duration_seconds)
    is_out_of_range = temperature > max_temp or temperature < min_temp
    is_alert = is_out_of_range and duration >= warning_seconds

    if is_alert:
        if temperature >= critical_temp or duration >= critical_seconds:
            severity = "critical"
        else:
            severity = "warning"
        message = (
            f"Alerta HACCP: temperatura {temperature}°C fuera del rango "
            f"[{min_temp}, {max_temp}]°C durante {duration} segundos."
        )
    elif is_out_of_range:
        severity = "warning"
        message = (
            f"Temperatura fuera de rango: {temperature}°C, pero aún no alcanza "
            f"el tiempo mínimo de alerta ({warning_seconds} s)."
        )
    else:
        severity = "normal"
        message = (
            f"Temperatura normal: {temperature}°C dentro del rango "
            f"[{min_temp}, {max_temp}]°C."
        )

    return {
        "is_alert": is_alert,
        "severity": severity,
        "temperature_c": temperature,
        "duration_seconds": duration,
        "threshold_c": max_temp,
        "rule": active_rule,
        "message": message,
    }


def evaluate_predictive_event(
    payload: Mapping[str, Any],
    rule: Any,
) -> dict[str, Any]:
    """Evalúa un evento predictivo con la regla HACCP activa de su cámara."""
    if not isinstance(payload, Mapping):
        raise ValueError("El evento predictivo debe ser un objeto.")

    event_values = {}
    for field in ("temperature", "remaining_time_min"):
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"El campo {field} debe ser un número.")
        try:
            number = float(value)
        except (OverflowError, TypeError, ValueError) as exc:
            raise ValueError(f"El campo {field} debe ser finito.") from exc
        if not math.isfinite(number):
            raise ValueError(f"El campo {field} debe ser finito.")
        event_values[field] = number

    if event_values["remaining_time_min"] < 0:
        raise ValueError("El campo remaining_time_min no puede ser negativo.")

    def rule_number(field: str) -> float:
        if isinstance(rule, Mapping):
            value = rule.get(field)
        else:
            value = getattr(rule, field, None)

        if value is None or isinstance(value, bool) or not isinstance(
            value, (int, float, Decimal)
        ):
            raise HaccpRuleConfigurationError(
                f"La regla HACCP activa requiere un valor numérico en {field}."
            )
        try:
            number = float(value)
        except (OverflowError, TypeError, ValueError) as exc:
            raise HaccpRuleConfigurationError(
                f"El valor de {field} en la regla HACCP no es compatible."
            ) from exc
        if not math.isfinite(number):
            raise HaccpRuleConfigurationError(
                f"El valor de {field} en la regla HACCP debe ser finito."
            )
        return number

    min_temp = rule_number("min_absolute_temp")
    max_temp = rule_number("max_absolute_temp")
    tolerance = rule_number("tolerance_time_min")
    if min_temp > max_temp:
        raise HaccpRuleConfigurationError(
            "La regla HACCP tiene min_absolute_temp mayor que max_absolute_temp."
        )
    if tolerance < 0:
        raise HaccpRuleConfigurationError(
            "La regla HACCP tiene tolerance_time_min negativa."
        )

    temperature = event_values["temperature"]
    remaining_time = event_values["remaining_time_min"]
    violations = []
    if temperature < min_temp:
        violations.append("temperature_below_minimum")
    if temperature > max_temp:
        violations.append("temperature_above_maximum")
    if remaining_time <= tolerance:
        violations.append("remaining_time_within_tolerance")

    if violations:
        message = (
            f"Alerta HACCP: temperatura {temperature}°C, tiempo restante "
            f"{remaining_time} min; infracciones: {', '.join(violations)}."
        )
    else:
        message = (
            f"Sin infracción HACCP: temperatura {temperature}°C dentro del "
            f"rango [{min_temp}, {max_temp}]°C y tiempo restante "
            f"{remaining_time} min sobre la tolerancia de {tolerance} min."
        )

    return {
        "is_alert": bool(violations),
        "temperature": temperature,
        "remaining_time_min": remaining_time,
        "min_absolute_temp": min_temp,
        "max_absolute_temp": max_temp,
        "tolerance_time_min": tolerance,
        "violations": violations,
        "message": message,
    }


def evaluate_temperature_series(
    temperatures: Iterable[float],
    sample_interval_seconds: int = 10,
    rule: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Evalúa una serie temporal de lecturas para detectar violaciones HACCP.

    La lógica asume que cada valor representa una muestra con un intervalo fijo.
    Para una secuencia continua fuera del rango, se calcula el tiempo total de
    violación multiplicando la cantidad de muestras por el intervalo.
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
    current_run_start = 0

    min_temp = float(active_rule.get("min_temp_c", float("-inf")))

    for index, value in enumerate(values):
        if value > max_temp or value < min_temp:
            if not current_run:
                current_run_start = index
            current_run.append(value)
        elif current_run:
            run_duration = (len(current_run) + 1) * sample_interval
            violating_runs.append(
                {
                    "start_index": current_run_start,
                    "length": len(current_run),
                    "duration_seconds": run_duration,
                    "max_temp_c": max(current_run),
                    "min_temp_c": min(current_run),
                }
            )
            current_run = []

    if current_run:
        run_duration = (len(current_run) + 1) * sample_interval
        violating_runs.append(
            {
                "start_index": current_run_start,
                "length": len(current_run),
                "duration_seconds": run_duration,
                "max_temp_c": max(current_run),
                "min_temp_c": min(current_run),
            }
        )

    total_violation_seconds = sum(item["duration_seconds"] for item in violating_runs)
    has_violation = total_violation_seconds >= warning_seconds

    if has_violation:
        severity = "critical" if total_violation_seconds >= float(active_rule["critical_duration_seconds"]) else "warning"
        message = (
            f"Se detectó una violación HACCP: {total_violation_seconds} segundos "
            f"fuera del rango [{min_temp}, {max_temp}]°C."
        )
    else:
        severity = "normal"
        message = (
            f"La serie está dentro del rango aceptable [{min_temp}, {max_temp}]°C "
            f"y ninguna ventana alcanza {warning_seconds} segundos."
        )

    return {
        "has_violation": has_violation,
        "total_violation_seconds": total_violation_seconds,
        "severity": severity,
        "rule": active_rule,
        "violations": violating_runs,
        "message": message,
    }


def validar_haccp(payload: Mapping[str, Any], rule: Any) -> dict[str, Any]:
    """Valida un evento Kafka usando medición y regla HACCP de una cámara.

    El evento debe incluir ``temperature_c`` y ``duration_seconds``. Las reglas
    ORM y los diccionarios usan los nombres oficiales del modelo de datos.
    """
    try:
        temperature = float(payload["temperature_c"])
        duration = float(payload["duration_seconds"])
    except (KeyError, TypeError, ValueError):
        return {
            "is_alert": False,
            "severity": "normal",
            "message": "Evento ignorado: se requieren temperature_c y duration_seconds.",
        }

    def rule_value(database_name: str, validator_name: str, default: Any) -> Any:
        if isinstance(rule, Mapping):
            return rule.get(database_name, rule.get(validator_name, default))
        return getattr(rule, database_name, getattr(rule, validator_name, default))

    if isinstance(rule, Mapping) and "tolerance_time_min" in rule:
        warning_seconds = float(rule["tolerance_time_min"]) * 60
    elif isinstance(rule, Mapping) and "warning_duration_seconds" in rule:
        warning_seconds = float(rule["warning_duration_seconds"])
    else:
        warning_seconds = float(rule_value(
            "tolerance_time_min",
            "warning_duration_seconds",
            DEFAULT_HACCP_RULE["warning_duration_seconds"] / 60,
        )) * 60

    mapped_rule = {
        "max_temp_c": float(rule_value("max_absolute_temp", "max_temp_c", DEFAULT_HACCP_RULE["max_temp_c"])),
        "min_temp_c": float(rule_value("min_absolute_temp", "min_temp_c", DEFAULT_HACCP_RULE["min_temp_c"])),
        "warning_duration_seconds": warning_seconds,
    }
    return evaluate_temperature_rule(temperature, duration, mapped_rule)


__all__ = [
    "DEFAULT_HACCP_RULE",
    "HaccpRuleConfigurationError",
    "evaluate_temperature_rule",
    "evaluate_temperature_series",
    "evaluate_predictive_event",
    "validar_haccp",
]
