from datetime import datetime, timedelta, timezone

import pytest

from predictor import calcular_pendiente, evaluar_riesgo


def test_calcular_pendiente_fits_linear_temperature_trend():
    assert calcular_pendiente([0, 60, 120], [-18, -17, -16]) == pytest.approx(1.0)


def test_calcular_pendiente_accepts_datetime_and_constant_timestamps():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    timestamps = [start, start + timedelta(minutes=1), start + timedelta(minutes=2)]

    assert calcular_pendiente(timestamps, [-18, -17, -16]) == pytest.approx(1.0)
    assert calcular_pendiente([10, 10], [-18, -16]) == 0.0


def test_calcular_pendiente_rejects_non_finite_measurements():
    assert calcular_pendiente([0, 60], [-18, float("nan")]) is None


def test_evaluar_riesgo_preserves_threshold_behavior():
    readings = [
        {"timestamp": index * 60, "temperature": -18 + index}
        for index in range(3)
    ]

    result = evaluar_riesgo(readings, absolute_max_temp=-10, umbral_alerta_minutos=40)

    assert result["pendiente_por_minuto"] == pytest.approx(1.0)
    assert result["tiempo_restante_min"] == pytest.approx(6.0)
    assert result["hay_riesgo"] is True
