"""Prueba de concepto (mock inicial) de Prophet.

El objetivo es:
  - Generar datos de ejemplo con pandas.
  - Devolver un DataFrame con columnas `ds` (fecha) e `y` (valor medido).
  - Entrenar un modelo Prophet y generar un pronóstico de prueba.

La columna `y` representa una magnitud a pronosticar (en el worker real
será el costo del kWh o el gasto eléctrico). Aquí se simula una serie
diaria con tendencia y estacionalidad semanal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_example_df(
    periods: int = 120,
    start: str = "2024-01-01",
    seed: int | None = 42,
) -> pd.DataFrame:
    """Devuelve un DataFrame con columnas `ds` e `y` usando datos de ejemplo.

    La serie se compone de una tendencia lineal, una componente semanal
    (sinusoidal) y un poco de ruido, lo que la vuelve apta para probar
    Prophet sin depender de datos reales.

    Args:
        periods: Número de observaciones diarias a generar.
        start: Fecha (YYYY-MM-DD) de la primera observación.
        seed: Semilla para reproducir el ruido (o None para no fijarla).

    Returns:
        DataFrame con columnas `ds` (datetime) e `y` (float).
    """
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
    """Entrena Prophet sobre datos de ejemplo y pronostica `horizon` días.

    Returns:
        (df, forecast) donde `df` es la serie con `ds`/`y` usada para
        entrenar y `forecast` es el DataFrame con las predicciones.
    """
    from prophet import Prophet

    if horizon <= 0:
        raise ValueError("horizon debe ser mayor o igual a 1")

    df = build_example_df(periods=periods, seed=seed)
    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=horizon, freq="D")
    forecast = model.predict(future)

    return df, forecast
