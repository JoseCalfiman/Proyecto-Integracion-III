"""Estadística descriptiva para series de temperatura o consumo."""

from typing import Optional, Sequence

import numpy as np

FACTOR_IQR = 1.5  # Multiplicador convencional de la regla de Tukey.


def _cuartiles(valores: np.ndarray) -> tuple[float, float]:
    # Interpolación lineal sobre las posiciones (n - 1) * q
    q1, q3 = np.percentile(valores, [25, 75], method="linear")
    return float(q1), float(q3)


def calcular_estadisticas(
    muestras: Sequence[float],
) -> dict[str, Optional[float]]:
    valores = np.asarray(muestras, dtype=float)
    conteo = len(valores)
    if not np.isfinite(valores).all():
        raise ValueError("La ventana contiene muestras no finitas")

    if conteo == 0:
        return dict.fromkeys(("media", "mediana", "std", "min", "max", "q1", "q3", "iqr")) | {
            "sample_count": 0,
        }

    q1, q3 = _cuartiles(valores)
    return {
        "sample_count": conteo,
        "media": float(valores.mean()),
        "mediana": float(np.median(valores)),
        "std": float(valores.std(ddof=1)) if conteo > 1 else None,
        "min": float(valores.min()),
        "max": float(valores.max()),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
    }

#Devuelve índices fuera de Q1/Q3 ampliados por FACTOR_IQR veces el IQR
def detectar_atipicos(muestras: Sequence[float]) -> list[int]:
    valores = np.asarray(muestras, dtype=float)
    if len(valores) == 0 or not np.isfinite(valores).all():
        return []

    q1, q3 = _cuartiles(valores)
    margen = FACTOR_IQR * (q3 - q1)
    fuera_de_limites = (valores < q1 - margen) | (valores > q3 + margen)
    return np.flatnonzero(fuera_de_limites).tolist()
