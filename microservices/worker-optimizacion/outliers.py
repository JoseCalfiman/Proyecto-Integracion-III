from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

IQR_K = 1.5
MIN_POINTS_FOR_IQR = 4


@dataclass(frozen=True)
class ConsumptionOutlierMark:
    """Marca IQR de un historial de consumo, con el dato original intacto."""

    frame: pd.DataFrame
    q1: float | None
    q3: float | None
    iqr: float | None
    lower: float | None
    upper: float | None
    k: float

    @property
    def outlier_count(self) -> int:
        if "is_outlier" not in self.frame.columns:
            return 0
        return int(self.frame["is_outlier"].sum())


def iqr_fences(values: pd.Series, k: float = IQR_K) -> dict[str, float] | None:
    """Calcula Q1, Q3 y las cercas de Tukey. ``None`` si no hay muestra suficiente."""
    _validate_k(k)
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    finite = numeric[np.isfinite(numeric)]
    if finite.size < MIN_POINTS_FOR_IQR:
        return None

    q1 = float(np.quantile(finite, 0.25))
    q3 = float(np.quantile(finite, 0.75))
    if not math.isfinite(q1) or not math.isfinite(q3):
        return None
    iqr = q3 - q1
    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower": q1 - k * iqr,
        "upper": q3 + k * iqr,
        "k": float(k),
    }


def mark_consumption_outliers(
    df: pd.DataFrame,
    value_col: str = "y",
    k: float = IQR_K,
) -> ConsumptionOutlierMark:
    """Marca consumos fuera de ``[Q1 - k*IQR, Q3 + k*IQR]``.

    No modifica ``df`` ni la columna original. ``y_original`` conserva el valor
    numérico y ``y_clean`` queda vacío en los atípicos para que el pronóstico
    no los use.
    """
    _validate_k(k)
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df debe ser un DataFrame")
    if value_col not in df.columns:
        raise ValueError(f"falta la columna {value_col}")

    marked = df.copy()
    original = pd.to_numeric(marked[value_col], errors="coerce")
    values = original.to_numpy(dtype=float)
    finite = np.isfinite(values)
    fences = iqr_fences(original, k=k)

    is_outlier = ~finite
    q1 = q3 = iqr = lower = upper = None
    if fences is not None:
        q1 = fences["q1"]
        q3 = fences["q3"]
        iqr = fences["iqr"]
        lower = fences["lower"]
        upper = fences["upper"]
        is_outlier = is_outlier | (
            finite & ((values < lower) | (values > upper))
        )

    clean = original.astype(float).mask(is_outlier)
    marked["y_original"] = original
    marked["is_outlier"] = np.asarray(is_outlier, dtype=bool)
    marked["y_clean"] = clean
    return ConsumptionOutlierMark(
        frame=marked,
        q1=q1,
        q3=q3,
        iqr=iqr,
        lower=lower,
        upper=upper,
        k=float(k),
    )


def outlier_records(mark: ConsumptionOutlierMark) -> list[dict[str, object]]:
    """Trazas de los atípicos: fecha, si existe, y consumo original."""
    frame = mark.frame
    if frame.empty or "is_outlier" not in frame.columns:
        return []

    records: list[dict[str, object]] = []
    flagged = frame.loc[frame["is_outlier"]]
    for _, row in flagged.iterrows():
        record: dict[str, object] = {"y_original": _finite_or_none(row["y_original"])}
        if "ds" in frame.columns and pd.notna(row["ds"]):
            ds = row["ds"]
            record["ds"] = ds.isoformat() if hasattr(ds, "isoformat") else str(ds)
        records.append(record)
    return records


def _validate_k(k: float) -> None:
    if not isinstance(k, (int, float)) or isinstance(k, bool) or not math.isfinite(k) or k < 0:
        raise ValueError("k debe ser mayor o igual a 0")


def _finite_or_none(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number
