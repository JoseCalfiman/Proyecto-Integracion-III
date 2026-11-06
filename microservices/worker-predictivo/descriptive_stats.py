"""Estadística descriptiva para series de temperatura o consumo."""

from typing import Optional, Sequence

import numpy as np


def _cuartiles(valores: np.ndarray) -> tuple[float, float]:
    # Interpolación lineal sobre las posiciones (n - 1) * q
    q1, q3 = np.percentile(valores, [25, 75], method="linear")
    return float(q1), float(q3)


def calcular_estadisticas(
    muestras: Sequence[float],
) -> dict[str, Optional[float]]:
    """Resume una serie finita. La desviación muestral requiere dos muestras."""
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


def detectar_atipicos(muestras: Sequence[float]) -> list[int]:
    """Devuelve los índices originales fuera de los límites de 1,5 IQR."""
    valores = np.asarray(muestras, dtype=float)
    if len(valores) == 0 or not np.isfinite(valores).all():
        return []

    q1, q3 = _cuartiles(valores)
    margen = 1.5 * (q3 - q1)
    fuera_de_limites = (valores < q1 - margen) | (valores > q3 + margen)
    return np.flatnonzero(fuera_de_limites).tolist()
