from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


TEMP_MIN_C = -50.0
TEMP_MAX_C = 50.0


class ContractError(ValueError):
    """El mensaje no cumple el contrato de sensor.raw."""


@dataclass(frozen=True)
class SensorReading:
    id_chamber: str
    timestamp: datetime  # siempre con zona horaria UTC
    temperature: float
    consumption_kw: Optional[float] = None


def _to_float(value: Any, campo: str) -> float:
    if value is None or isinstance(value, bool):
        raise ContractError(f"'{campo}' ausente o con tipo inválido: {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ContractError(f"'{campo}' no es numérico: {value!r}") from None
    if not math.isfinite(number):
        raise ContractError(f"'{campo}' no es un número finito: {value!r}")
    return number


def _primero(data: dict, *nombres: str) -> Any:
    """Devuelve el primer campo presente (no None) entre los nombres dados."""
    for nombre in nombres:
        if data.get(nombre) is not None:
            return data[nombre]
    return None


def parse_timestamp(raw: Any) -> datetime:
    """Convierte ISO 8601 o epoch (s/ms) a datetime con zona UTC."""
    if raw is None or isinstance(raw, bool):
        raise ContractError(f"'timestamp' ausente o inválido: {raw!r}")

    try:
        if isinstance(raw, (int, float)):
            if not math.isfinite(raw):
                raise ContractError(f"'timestamp' no es finito: {raw!r}")
            seconds = raw / 1000.0 if raw > 2e10 else float(raw)
            return datetime.fromtimestamp(seconds, tz=timezone.utc)

        if isinstance(raw, str):
            texto = raw.strip()
            try:
                return parse_timestamp(float(texto))  # epoch enviado como texto
            except ValueError:
                pass
            parsed = datetime.fromisoformat(texto.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise ContractError(f"'timestamp' con formato inválido: {raw!r}") from None

    raise ContractError(f"'timestamp' con tipo inválido: {type(raw).__name__}")


def parse_sensor_reading(data: Any) -> SensorReading:
    """Valida y normaliza un mensaje de sensor.raw. Lanza ContractError si no cumple."""
    if not isinstance(data, dict):
        raise ContractError(f"el mensaje debe ser un objeto JSON, llegó {type(data).__name__}")

    raw_chamber = _primero(data, "id_chamber", "chamber_id")
    if raw_chamber is None:
        raise ContractError("falta 'id_chamber' (o su alias 'chamber_id')")
    try:
        id_chamber = str(uuid.UUID(str(raw_chamber)))
    except ValueError:
        raise ContractError(f"'id_chamber' no es un UUID válido: {raw_chamber!r}") from None

    timestamp = parse_timestamp(_primero(data, "timestamp", "recorded_at"))
    temperature = _to_float(data.get("temperature"), "temperature")
    if not TEMP_MIN_C <= temperature <= TEMP_MAX_C:
        raise ContractError(
            f"'temperature' fuera de rango [{TEMP_MIN_C}, {TEMP_MAX_C}]: {temperature}"
        )

    consumption_kw: Optional[float] = None
    if data.get("consumption_kw") is not None:
        try:
            consumption_kw = _to_float(data["consumption_kw"], "consumption_kw")
        except ContractError:
            consumption_kw = None  # campo opcional: no vale la pena perder la lectura

    return SensorReading(
        id_chamber=id_chamber,
        timestamp=timestamp,
        temperature=temperature,
        consumption_kw=consumption_kw,
    )
