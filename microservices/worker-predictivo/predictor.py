from datetime import datetime
from typing import List, Optional, Union
from sklearn.linear_model import LinearRegression
import numpy as np

TimestampLike = Union[datetime, float, int]

# Convierte la lista de timestamps (datetime o números) a
# segundos relativos al primer dato.
def _timestamps_a_segundos(timestamps: List[TimestampLike]) -> np.ndarray:
    if isinstance(timestamps[0], datetime):
        base = timestamps[0]
        return np.array(
            [(ts - base).total_seconds() for ts in timestamps],
            dtype=float,
        )
    return np.array(timestamps, dtype=float) - float(timestamps[0])


# Calcula la pendiente de calentamiento (°C/min)
def calcular_pendiente(
    timestamps: List[TimestampLike],
    temperaturas: List[float],
) -> Optional[float]:
    if len(timestamps) != len(temperaturas):
        raise ValueError("timestamps y temperaturas deben tener la misma longitud")

    if len(temperaturas) < 2:
        return None

    segundos = _timestamps_a_segundos(timestamps)
    X = segundos.reshape(-1, 1)
    y = np.array(temperaturas, dtype=float)

    modelo = LinearRegression()
    modelo.fit(X, y)

    pendiente_por_segundo = modelo.coef_[0]
    pendiente_por_minuto = pendiente_por_segundo * 60.0

    return float(pendiente_por_minuto)

def estimar_tiempo_restante(
    temperatura_actual: float,
    absolute_max_temp: float,
    pendiente_por_minuto: float,
) -> Optional[float]:
    if pendiente_por_minuto <= 0:
        return None
    if temperatura_actual >= absolute_max_temp:
        return 0.0

    return (absolute_max_temp - temperatura_actual) / pendiente_por_minuto

def determinar_nivel_riesgo(
    tiempo_restante_min: Optional[float],
    umbral_alerta_minutos: float = 40.0,
) -> str:
    if tiempo_restante_min is None:
        return "SIN_RIESGO"
    if tiempo_restante_min <= umbral_alerta_minutos * 0.25:
        return "CRITICO"
    if tiempo_restante_min <= umbral_alerta_minutos * 0.6:
        return "ALTO"
    if tiempo_restante_min <= umbral_alerta_minutos:
        return "MEDIO"
    return "BAJO"

# Combina pendiente + tiempo restante y determina si hay riesgo.
def evaluar_riesgo(
    buffer: List[dict],
    absolute_max_temp: float,
    umbral_alerta_minutos: float = 40.0,
) -> dict:

    if len(buffer) < 2:
        return {
            "pendiente_por_minuto": None,
            "tiempo_restante_min": None,
            "hay_riesgo": False,
            "nivel_riesgo": "SIN_RIESGO",
        }

    timestamps = [d["timestamp"] for d in buffer]
    temperaturas = [d["temperature"] for d in buffer]

    pendiente = calcular_pendiente(timestamps, temperaturas)
    if pendiente is None:
        return {
            "pendiente_por_minuto": None,
            "tiempo_restante_min": None,
            "hay_riesgo": False,
            "nivel_riesgo": "SIN_RIESGO",
        }

    tiempo_restante = estimar_tiempo_restante(
        temperatura_actual=temperaturas[-1],
        absolute_max_temp=absolute_max_temp,
        pendiente_por_minuto=pendiente,
    )

    hay_riesgo = tiempo_restante is not None and tiempo_restante <= umbral_alerta_minutos
    nivel_riesgo = determinar_nivel_riesgo(tiempo_restante, umbral_alerta_minutos)

    return {
        "pendiente_por_minuto": pendiente,
        "tiempo_restante_min": tiempo_restante,
        "hay_riesgo": hay_riesgo,
        "nivel_riesgo": nivel_riesgo,
    }


if __name__ == "__main__":
    timestamps_test = [0, 60, 120, 180] # segundos
    temps_test = [20.0, 21.0, 22.0, 23.0]

    pendiente_val = calcular_pendiente(timestamps_test, temps_test)
    print(f"Pendiente calculada: {pendiente_val:.2f} °C/min (Esperada: 1.0)")
    assert abs(pendiente_val - 1.0) < 1e-5, "Error en el cálculo de la pendiente"

    limite_haccp = 28.0
    tiempo_val = estimar_tiempo_restante(
        temperatura_actual=temps_test[-1],
        absolute_max_temp=limite_haccp,
        pendiente_por_minuto=pendiente_val,
    )
    print(f"Tiempo restante estimado: {tiempo_val:.1f} min (Esperado: 5.0)")
    assert abs(tiempo_val - 5.0) < 1e-5, "Error en el cálculo del tiempo restante"

    riesgo_val = determinar_nivel_riesgo(tiempo_val, umbral_alerta_minutos=40.0)
    print(f"Nivel de riesgo determinado: {riesgo_val}")
    
    print("Validación de regresión y tiempo restante superada con éxito")