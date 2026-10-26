from __future__ import annotations

import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

# Nombres de campo aceptados en el payload de sensor.raw, en orden de prioridad.
_TS_FIELDS = ("timestamp", "ts", "time", "fecha", "datetime")
_ENERGY_FIELDS = (
    "consumption_kwh",
    "consumo_kwh",
    "consumo",
    "kwh",
    "energy_kwh",
)
_POWER_FIELDS = (
    "consumption_kw",
    "consumo_kw",
    "power_kw",
    "potencia_kw",
)
_TEMPERATURE_FIELDS = ("temperature", "temperatura", "temp")
_SENSOR_FIELDS = ("sensor_id", "sensor", "id", "device_id")
_CHAMBER_FIELDS = ("id_chamber", "chamber_id")

# Evita que una caída prolongada del sensor convierta todo el intervalo en consumo.
_MAX_INTERVAL_SECONDS = 300.0


def _first(data: dict[str, Any], fields: Iterable[str]) -> Any:
    for field in fields:
        if field in data and data[field] is not None:
            return data[field]
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        ts = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        ts = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str) and value.strip():
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(parsed):
            return None
        ts = parsed.to_pydatetime()
    else:
        return None

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
    """Normaliza un payload crudo de ``sensor.raw`` a un formato interno.

    ``sensor.raw`` actualmente publica potencia instantánea en ``consumption_kw``.
    También se mantienen aliases históricos en kWh para compatibilidad.

    Devuelve ``None`` si falta el timestamp o no hay consumo/temperatura útiles.
    No inventa la fecha: sin timestamp el dato no entra al historial de Prophet.
    """
    if not isinstance(data, dict):
        return None

    ts = _parse_timestamp(_first(data, _TS_FIELDS))
    if ts is None:
        return None

    consumption_kwh = _to_float(_first(data, _ENERGY_FIELDS))
    consumption_kw = _to_float(_first(data, _POWER_FIELDS))
    temperature = _to_float(_first(data, _TEMPERATURE_FIELDS))

    if consumption_kwh is None and consumption_kw is None and temperature is None:
        return None

    return {
        "ts": ts,
        "consumption_kwh": consumption_kwh,
        "consumption_kw": consumption_kw,
        "temperature": temperature,
        "id_chamber": _first(data, _CHAMBER_FIELDS),
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

    @staticmethod
    def _day(ts: datetime) -> pd.Timestamp:
        return pd.Timestamp(ts).tz_convert("UTC").tz_localize(None).normalize()

    def to_dataframe(self) -> pd.DataFrame:
        """Agrega energía diaria en columnas ``ds`` / ``y`` para Prophet.

        - Si una lectura ya trae ``consumption_kwh``, se suma directamente.
        - Si trae ``consumption_kw``, se integra la potencia hasta la siguiente
          lectura de la misma cámara/sensor: ``kWh = kW * segundos / 3600``.
        - Cada intervalo se limita a 300 s para no inflar consumo por huecos.
        """
        readings = self.snapshot()
        daily_energy: dict[pd.Timestamp, float] = defaultdict(float)

        # Lecturas que ya representan energía.
        for reading in readings:
            energy = reading.get("consumption_kwh")
            if energy is not None:
                daily_energy[self._day(reading["ts"])] += float(energy)

        # Lecturas de potencia instantánea. Si también existe kWh en la misma
        # lectura, se prioriza kWh para evitar doble contabilización.
        power_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for reading in readings:
            if reading.get("consumption_kwh") is not None:
                continue
            if reading.get("consumption_kw") is None:
                continue

            source = (
                reading.get("id_chamber")
                or reading.get("sensor_id")
                or "__default__"
            )
            power_groups[str(source)].append(reading)

        for group in power_groups.values():
            group.sort(key=lambda item: item["ts"])
            for current, nxt in zip(group, group[1:]):
                seconds = (nxt["ts"] - current["ts"]).total_seconds()
                if seconds <= 0:
                    continue

                seconds = min(seconds, _MAX_INTERVAL_SECONDS)
                energy_kwh = float(current["consumption_kw"]) * seconds / 3600.0
                daily_energy[self._day(current["ts"])] += energy_kwh

        if not daily_energy:
            return pd.DataFrame(columns=["ds", "y"])

        rows = [
            {"ds": day, "y": float(value)}
            for day, value in sorted(daily_energy.items(), key=lambda item: item[0])
        ]
        return pd.DataFrame(rows, columns=["ds", "y"])


# Buffer compartido por el consumer y el scheduler dentro del mismo proceso.
readings_buffer = ReadingsBuffer()


def get_buffer() -> ReadingsBuffer:
    return readings_buffer
