from datetime import datetime
from typing import List, Optional, Union
from sklearn.linear_model import LinearRegression
import numpy as np


TimestampLike = Union[datetime, float, int]

#Convierte la lista de timestamps (datetime o números) a segundos relativos al primer dato
def _timestamps_a_segundos(timestamps: List[TimestampLike]) -> np.ndarray:
    if isinstance(timestamps[0], datetime):
        base = timestamps[0]
        return np.array(
            [(ts - base).total_seconds() for ts in timestamps],
            dtype=float,
        )
    return np.array(timestamps, dtype=float) - float(timestamps[0])


#Calcula la pendiente de calentamiento (°C/min)
def calcular_pendiente(
    timestamps: List[TimestampLike],
    temperaturas: List[float],
) -> Optional[float]:
    if len(timestamps) != len(temperaturas):
        raise ValueError("timestamps y temperaturas deben tener la misma longitud")

    if len(temperaturas) < 2:
        # No hay suficientes puntos para ajustar una recta
        return None

    segundos = _timestamps_a_segundos(timestamps)
    X = segundos.reshape(-1, 1)
    y = np.array(temperaturas, dtype=float)

    modelo = LinearRegression()
    modelo.fit(X, y)

    pendiente_por_segundo = modelo.coef_[0]
    pendiente_por_minuto = pendiente_por_segundo * 60.0

    return float(pendiente_por_minuto)


#Estima cuántos minutos faltan para llegar al límite HACCP según la pendiente actual
def estimar_tiempo_restante(
    temperatura_actual: float,
    limite_haccp: float,
    pendiente_por_minuto: float,
) -> Optional[float]:
    if pendiente_por_minuto <= 0:
        return None
    if temperatura_actual >= limite_haccp:
        return 0.0

    return (limite_haccp - temperatura_actual) / pendiente_por_minuto


# Combina pendiente + tiempo restante y determina si hay riesgo
def evaluar_riesgo(
    buffer: List[dict],
    limite_haccp: float,
    umbral_alerta_minutos: float = 40.0,
) -> dict:

    if len(buffer) < 2:
        return {
            "pendiente_por_minuto": None,
            "tiempo_restante_min": None,
            "hay_riesgo": False,
        }

    timestamps = [d["timestamp"] for d in buffer]
    temperaturas = [d["temperatura"] for d in buffer]

    pendiente = calcular_pendiente(timestamps, temperaturas)
    if pendiente is None:
        return {
            "pendiente_por_minuto": None,
            "tiempo_restante_min": None,
            "hay_riesgo": False,
        }

    tiempo_restante = estimar_tiempo_restante(
        temperatura_actual=temperaturas[-1],
        limite_haccp=limite_haccp,
        pendiente_por_minuto=pendiente,
    )

    hay_riesgo = tiempo_restante is not None and tiempo_restante <= umbral_alerta_minutos

    return {
        "pendiente_por_minuto": pendiente,
        "tiempo_restante_min": tiempo_restante,
        "hay_riesgo": hay_riesgo,
    }


if __name__ == "__main__":
    ejemplo_timestamps = [0, 60, 120, 180, 240, 300]
    ejemplo_temperaturas = [-18.0, -17.5, -17.0, -16.6, -16.1, -15.5]

    pendiente = calcular_pendiente(ejemplo_timestamps, ejemplo_temperaturas)
    print(f"Pendiente: {pendiente:.3f} °C/min")

    tiempo_restante = estimar_tiempo_restante(
        temperatura_actual=ejemplo_temperaturas[-1],
        limite_haccp=-10.0,
        pendiente_por_minuto=pendiente,
    )
    print(f"Tiempo restante estimado: {tiempo_restante:.1f} min")