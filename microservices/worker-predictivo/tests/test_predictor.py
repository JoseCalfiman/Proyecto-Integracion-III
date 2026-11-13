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


def test_evaluar_riesgo_registra_lecturas_atipicas(caplog):
    timestamps = [0, 60, 120, 180, 240]
    temperaturas = [-18, -18.1, -17.9, -18, 20]
    lecturas = [
        {"timestamp": timestamp, "temperature": temperatura}
        for timestamp, temperatura in zip(timestamps, temperaturas)
    ]

    resultado = evaluar_riesgo(lecturas, absolute_max_temp=-10)

    assert "outlier_count=1" in caplog.text
    assert str(lecturas[-1]) in caplog.text
    assert resultado["pendiente_por_minuto"] == pytest.approx(0.02)
    assert calcular_pendiente(timestamps, temperaturas) > 7
    assert resultado["hay_riesgo"] is False
    assert resultado["diagnostico"]["outliers"] == [{"index": 4, **lecturas[-1]}]
    assert len(lecturas) == 5


def test_spike_no_se_usa_como_temperatura_actual():
    temperaturas = [-18, -17.9, -17.8, -17.7, 20]
    resultado = evaluar_riesgo(
        [{"timestamp": i * 60, "temperature": t} for i, t in enumerate(temperaturas)],
        absolute_max_temp=-10,
    )
    assert resultado["pendiente_por_minuto"] == pytest.approx(0.1)
    assert resultado["tiempo_restante_min"] == pytest.approx(77)
    assert resultado["hay_riesgo"] is False


@pytest.mark.parametrize(
    ("temperaturas", "condiciones", "std", "iqr", "atipicos"),
    [
        ([], ["VENTANA_INSUFICIENTE"], None, None, 0),
        ([-18], ["VENTANA_INSUFICIENTE"], None, 0, 0),
        ([-18, -18, -18], [], 0, 0, 0),
        ([-18, -17, -16], ["DATOS_VARIABLES"], 1, 1, 0),
        ([-18, -18, -18, -18, 20], ["DATOS_VARIABLES", "CON_ATIPICOS"], 38 / 5 ** 0.5, 0, 1),
    ],
)
def test_diagnostico_ventana(temperaturas, condiciones, std, iqr, atipicos):
    resultado = evaluar_riesgo(
        [{"timestamp": i * 60, "temperature": t} for i, t in enumerate(temperaturas)],
        absolute_max_temp=-10,
    )
    diagnostico = resultado["diagnostico"]
    assert diagnostico["sample_count"] == len(temperaturas)
    assert diagnostico["span_minutes"] == (len(temperaturas) - 1 if temperaturas else None)
    assert diagnostico["std_temp"] == pytest.approx(std) if std is not None else diagnostico["std_temp"] is None
    assert diagnostico["iqr_temp"] == iqr
    assert diagnostico["outlier_count"] == atipicos
    assert diagnostico["condiciones"] == condiciones


def test_diagnostico_sin_separacion_temporal():
    resultado = evaluar_riesgo(
        [{"timestamp": 60, "temperature": -18}, {"timestamp": 60, "temperature": -17}],
        absolute_max_temp=-10,
    )
    assert resultado["pendiente_por_minuto"] is None
    assert "VENTANA_INSUFICIENTE" in resultado["diagnostico"]["condiciones"]


def test_diagnostico_acepta_datetime_y_umbral_configurable():
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    resultado = evaluar_riesgo(
        [{"timestamp": inicio + timedelta(minutes=i), "temperature": -18 + i} for i in range(3)],
        absolute_max_temp=-10,
        umbral_std_temp=2,
    )
    assert resultado["diagnostico"]["span_minutes"] == 2
    assert resultado["diagnostico"]["condiciones"] == []


def test_datos_no_finitos_no_producen_prediccion():
    resultado = evaluar_riesgo(
        [{"timestamp": 0, "temperature": -18}, {"timestamp": 60, "temperature": float("nan")}],
        absolute_max_temp=-10,
    )
    assert resultado["pendiente_por_minuto"] is None
    assert resultado["diagnostico"]["std_temp"] is None
    assert resultado["diagnostico"]["condiciones"] == ["VENTANA_INSUFICIENTE"]
