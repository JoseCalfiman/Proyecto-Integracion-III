from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

# Nombres de campo aceptados en el payload de sensor.raw, en orden de prioridad.
_TS_FIELDS = ("timestamp", "ts", "time", "fecha", "datetime")
_CONSUMPTION_FIELDS = (
    "consumption_kwh",
    "consumo_kwh",
    "consumo",
    "kwh",
    "energy_kwh",
)
_TEMPERATURE_FIELDS = ("temperature", "temperatura", "temp")
_SENSOR_FIELDS = ("sensor_id", "sensor", "id", "device_id")


def _first(data: dict[str, Any], fields: Iterable[str]) -> Any:
    for field in fields:
        if field in data and data[field] is not None:
            return data[field]
    return None


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        ts = value
    elif isinstance(value, (int, float)):
        ts = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str) and value.strip():
        ts = pd.to_datetime(value, utc=True).to_pydatetime()
    else:
        ts = datetime.now(timezone.utc)

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_reading(data: dict[str, Any]) -> dict[str, Any] | None:
    """Normaliza un payload crudo de sensor.raw a un formato interno.

    Devuelve ``None`` cuando no hay timestamp ni consumo/temperatura utiles.
    """
    if not isinstance(data, dict):
        return None

    consumption = _to_float(_first(data, _CONSUMPTION_FIELDS))
    temperature = _to_float(_first(data, _TEMPERATURE_FIELDS))
    if consumption is None and temperature is None:
        return None

    return {
        "ts": _parse_timestamp(_first(data, _TS_FIELDS)),
        "consumption_kwh": consumption,
        "temperature": temperature,
        "sensor_id": _first(data, _SENSOR_FIELDS),
    }


class ReadingsBuffer:
    """Buffer en memoria, thread-safe, con las lecturas recientes de sensores."""

    def __init__(self, maxlen: int = 100_000) -> None:
        self._lock = threading.Lock()
        self._readings: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def add(self, reading: dict[str, Any]) -> None:
        with self._lock:
            self._readings.append(reading)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._readings)

    def __len__(self) -> int:
        with self._lock:
            return len(self._readings)

    def clear(self) -> None:
        with self._lock:
            self._readings.clear()

    def to_dataframe(self) -> pd.DataFrame:
        """Agrega el consumo por dia en columnas ``ds`` / ``y`` (para Prophet)."""
        readings = self.snapshot()
        rows = [
            {
                "ds": pd.Timestamp(r["ts"]).tz_convert("UTC").tz_localize(None).normalize(),
                "y": r["consumption_kwh"],
            }
            for r in readings
            if r.get("consumption_kwh") is not None
        ]
        if not rows:
            return pd.DataFrame(columns=["ds", "y"])

        df = pd.DataFrame(rows)
        daily = (
            df.groupby("ds", as_index=False)["y"]
            .sum()
            .sort_values("ds")
            .reset_index(drop=True)
        )
        daily["y"] = daily["y"].astype(float)
        return daily


# Buffer compartido por el consumer y el scheduler dentro del mismo proceso.
readings_buffer = ReadingsBuffer()


def get_buffer() -> ReadingsBuffer:
    return readings_buffer
