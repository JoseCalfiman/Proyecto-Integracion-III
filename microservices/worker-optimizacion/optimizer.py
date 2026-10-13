from __future__ import annotations
import numpy as np
import pandas as pd

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


def forecast_daily_consumption(
    df: pd.DataFrame,
    horizon: int = 1,
    freq: str = "D",
) -> pd.DataFrame | None:
    """Ajusta Prophet sobre consumo diario real y predice ``horizon`` dias.

    ``df`` debe tener columnas ``ds`` (fechas) e ``y`` (kWh por dia). Devuelve
    el DataFrame de Prophet (con ``yhat``, ``yhat_lower``, ``yhat_upper``) o
    ``None`` si no hay suficientes datos.
    """
    if horizon <= 0:
        raise ValueError("horizon debe ser mayor o igual a 1")
    if df is None or df.empty or len(df) < MIN_DAILY_POINTS:
        return None

    from prophet import Prophet

    model = Prophet()
    model.fit(df[["ds", "y"]])
    future = model.make_future_dataframe(periods=horizon, freq=freq)
    return model.predict(future)
