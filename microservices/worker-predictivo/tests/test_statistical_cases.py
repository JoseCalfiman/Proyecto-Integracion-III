"""M6: valores esperados derivados a mano para estadística y predicción."""
import pytest

from descriptive_stats import calcular_estadisticas, detectar_atipicos
from predictor import calcular_pendiente, estimar_tiempo_restante, evaluar_riesgo


def test_media_cambia_ante_extremo_y_mediana_se_conserva():
    base = calcular_estadisticas([-18, -18, -18, -18, -18])
    extremo = calcular_estadisticas([-18, -18, -18, -18, 20])
    assert base["media"] == base["mediana"] == -18
    assert extremo["media"] == pytest.approx(-10.4)
    assert extremo["mediana"] == -18


def test_desviacion_cero_en_serie_estable():
    assert calcular_estadisticas([-18] * 5)["std"] == 0


def test_cuartiles_interpolados_e_iqr():
    estadisticas = calcular_estadisticas([1, 2, 3, 4])
    assert estadisticas["q1"] == 1.75
    assert estadisticas["q3"] == 3.25
    assert estadisticas["iqr"] == 1.5


def test_atipico_identifica_posicion_sin_mutar_serie():
    serie = [-18, -18.1, -17.9, -18, 20]
    assert detectar_atipicos(serie) == [4]
    assert serie == [-18, -18.1, -17.9, -18, 20]


def test_tendencia_creciente_un_grado_por_minuto():
    assert calcular_pendiente([0, 60, 120], [-18, -17, -16]) == 1


def test_tendencia_decreciente_no_produce_alerta_predictiva():
    ventana = [{"timestamp": i * 60, "temperature": t} for i, t in enumerate([-16, -17, -18])]
    resultado = evaluar_riesgo(ventana, absolute_max_temp=-10)
    assert resultado["pendiente_por_minuto"] == -1
    assert resultado["tiempo_restante_min"] is None
    assert resultado["hay_riesgo"] is False


def test_tiempo_restante_hasta_limite():
    # Faltan 6 °C, a razón de 1 °C/min.
    assert estimar_tiempo_restante(-16, -10, 1) == 6


def test_pendiente_usa_tiempos_irregulares_reales():
    assert calcular_pendiente([0, 30, 120], [-18, -17.5, -16]) == 1


def test_limite_alcanzado_con_pendiente_positiva():
    assert estimar_tiempo_restante(-10, -10, 1) == 0


def test_atipico_interior_conserva_distancia_temporal():
    temperaturas = [-18, -17.9, 20, -17.7, -17.6]
    resultado = evaluar_riesgo(
        [{"timestamp": i * 60, "temperature": t} for i, t in enumerate(temperaturas)],
        absolute_max_temp=-10,
    )
    assert resultado["pendiente_por_minuto"] == pytest.approx(0.1)
    assert resultado["tiempo_restante_min"] == pytest.approx(76)
    assert resultado["diagnostico"]["outliers"][0]["index"] == 2
