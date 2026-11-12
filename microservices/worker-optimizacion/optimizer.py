from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from outliers import mark_consumption_outliers, outlier_records

logger = logging.getLogger(__name__)

# Minimo de observaciones diarias para poder ajustar Prophet.
MIN_DAILY_POINTS = 2

def build_example_df(
    periods: int = 120,
    start: str = "2024-01-01",
    seed: int | None = 42,
) -> pd.DataFrame:
    
    dates = pd.date_range(start=start, periods=periods, freq="D")
    rng = np.random.default_rng(seed)
    t = pd.Series(range(periods), dtype=float)
    trend = 10.0 + 0.05 * t
    weekly = 3.0 * pd.Series(
        [((i % 7) - 3) / 3 for i in range(periods)], dtype=float
    )
    noise = pd.Series(rng.normal(0.0, 0.8, size=periods), dtype=float)

    y = trend + weekly + noise

    return pd.DataFrame({"ds": dates, "y": y})

def forecast_example(
    periods: int = 120,
    horizon: int = 7,
    seed: int | None = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    
    from prophet import Prophet

    if horizon <= 0:
        raise ValueError("horizon debe ser mayor o igual a 1")

    df = build_example_df(periods=periods, seed=seed)
    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=horizon, freq="D")
    forecast = model.predict(future)

    return df, forecast


def prepare_prophet_history(df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Arma el historial diario ``ds``/``y`` que debe recibir Prophet.

    Descarta filas sin fecha o sin kWh y agrega por dia. Devuelve ``None`` si,
    despues de limpiar, no hay observaciones suficientes: no se inventa serie.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if "ds" not in df.columns or "y" not in df.columns:
        return None

    history = pd.DataFrame(
        {
            "ds": pd.to_datetime(df["ds"], utc=True, errors="coerce"),
            "y": pd.to_numeric(df["y"], errors="coerce"),
        }
    )
    history = history.dropna(subset=["ds", "y"])
    if history.empty:
        return None

    history["ds"] = history["ds"].dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    history = (
        history.groupby("ds", as_index=False)["y"]
        .sum()
        .sort_values("ds")
        .reset_index(drop=True)
    )
    history["y"] = history["y"].astype(float)
    if len(history) < MIN_DAILY_POINTS:
        return None
    return history


def _history_without_outliers(
    history: pd.DataFrame,
) -> tuple[pd.DataFrame | None, list[dict[str, object]]]:
    """Excluye consumos atípicos del ajuste. El historial original no se modifica."""
    mark = mark_consumption_outliers(history)
    records = outlier_records(mark)
    if records:
        logger.info(
            "[optimizer] %d consumo(s) atípico(s) marcado(s) con IQR "
            "(Q1=%s, Q3=%s, IQR=%s); se conserva el dato original "
            "y no entra al pronóstico: %s",
            len(records),
            mark.q1,
            mark.q3,
            mark.iqr,
            records,
        )

    training = (
        mark.frame.loc[~mark.frame["is_outlier"], ["ds", "y"]]
        .reset_index(drop=True)
    )
    if len(training) < MIN_DAILY_POINTS:
        logger.warning(
            "[optimizer] tras marcar outliers con IQR quedan %d dias; "
            "no se inventa prediccion",
            len(training),
        )
        return None, records
    return training, records


def _periods_until(last_training_ds: pd.Timestamp, target_end: pd.Timestamp, freq: str) -> int:
    offset = pd.tseries.frequencies.to_offset(freq)
    periods = 0
    cursor = pd.Timestamp(last_training_ds)
    target = pd.Timestamp(target_end)
    while cursor < target:
        cursor = cursor + offset
        periods += 1
    return periods


def forecast_daily_consumption(
    df: pd.DataFrame,
    horizon: int = 1,
    freq: str = "D",
) -> pd.DataFrame | None:
    """Ajusta Prophet sobre consumo diario real y predice ``horizon`` dias.

    ``df`` debe tener columnas ``ds`` (fechas) e ``y`` (kWh por dia). Antes del
    ajuste marca outliers con IQR y los deja fuera del modelo, sin reescribir el
    dato original. Devuelve el DataFrame de Prophet (con ``yhat``,
    ``yhat_lower``, ``yhat_upper``) o ``None`` si faltan datos. Nunca completa
    el historial con valores inventados.
    """
    if horizon <= 0:
        raise ValueError("horizon debe ser mayor o igual a 1")

    history = prepare_prophet_history(df)
    if history is None:
        return None

    training, outliers = _history_without_outliers(history)
    if training is None:
        return None

    from prophet import Prophet

    try:
        model = Prophet()
        model.fit(training)
        periods = _periods_until(
            pd.Timestamp(training["ds"].iloc[-1]),
            pd.Timestamp(history["ds"].iloc[-1]) + horizon * pd.tseries.frequencies.to_offset(freq),
            freq,
        )
        future = model.make_future_dataframe(periods=periods, freq=freq)
        forecast = model.predict(future)
        forecast.attrs["consumption_outliers"] = outliers
        return forecast
    except Exception as exc:
        logger.warning(
            "[optimizer] Prophet no pudo estimar el consumo; no se inventa prediccion: %s",
            exc,
        )
        return None
