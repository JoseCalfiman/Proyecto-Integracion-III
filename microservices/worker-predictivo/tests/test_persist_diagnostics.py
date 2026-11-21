"""Contrato de persistencia M5: diagnóstico JSON dentro de la misma predicción."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from haccp_predictions import guardar_prediccion
from predictor import evaluar_riesgo


def test_diagnostico_se_guarda_con_timestamps_y_estadisticas():
    inicio = datetime(2026, 11, 20, tzinfo=timezone.utc)
    ventana = [
        {"timestamp": inicio + timedelta(minutes=i),
         "temperature": temperatura, "consumption_kw": 2}
        for i, temperatura in enumerate([-18, -18, -18, -18, 20])
    ]
    resultado = evaluar_riesgo(ventana, absolute_max_temp=-10)
    agregadas = []
    commits = []
    session = SimpleNamespace(
        add=agregadas.append,
        commit=lambda: commits.append(True),
        refresh=lambda prediccion: None,
    )
    prediccion = guardar_prediccion(
        session, "55555555-5555-5555-5555-555555555555",
        resultado["pendiente_por_minuto"], None, resultado["tiempo_restante_min"],
        resultado["nivel_riesgo"], diagnostico=resultado["diagnostico"],
    )
    assert agregadas == [prediccion]
    assert len(commits) == 1
    diagnostico = json.loads(json.dumps(prediccion.diagnostico, allow_nan=False))
    assert diagnostico["outliers"][0]["timestamp"] == "2026-11-20T00:04:00+00:00"
    assert diagnostico["reference_timestamp"] == "2026-11-20T00:03:00+00:00"
    assert diagnostico["temperature"]["sample_count"] == 5
    assert diagnostico["consumption_kw"]["media"] == 2
    assert diagnostico["outlier_count"] == 1
