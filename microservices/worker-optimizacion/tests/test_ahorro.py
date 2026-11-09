import pytest

from ahorro import (
    Action,
    calcular_ahorro_action,
    calcular_ahorro_potencial,
    es_recomendacion_util,
    generar_textos_recomendacion,
)


def test_calcular_ahorro_potencial_basic():
    assert calcular_ahorro_potencial(10.0, 2, 145.0) == 2900.0


def test_calcular_ahorro_potencial_zero_hours():
    assert calcular_ahorro_potencial(10.0, 0, 145.0) == 0.0


def test_calcular_ahorro_potencial_zero_price():
    assert calcular_ahorro_potencial(10.0, 2, 0.0) == 0.0


def test_calcular_ahorro_potencial_negative_power_raises():
    with pytest.raises(ValueError):
        calcular_ahorro_potencial(-1.0, 2, 145.0)


def test_calcular_ahorro_potencial_negative_hours_raises():
    with pytest.raises(ValueError):
        calcular_ahorro_potencial(10.0, -1, 145.0)


def test_calcular_ahorro_potencial_negative_price_raises():
    with pytest.raises(ValueError):
        calcular_ahorro_potencial(10.0, 2, -145.0)


def test_calcular_ahorro_action_uses_action_hours():
    action = Action(
        equipment="compresor",
        action="apagar",
        hours=2,
        window=["18:00", "22:00"],
    )
    assert calcular_ahorro_action(action, potencia_kw=10.0, precio_clp_kwh=145.0) == 2900.0


def test_action_default_window_is_empty():
    action = Action(equipment="compresor", action="apagar", hours=2)
    assert action.window == []


@pytest.mark.parametrize(
    ("monto", "porcentaje"),
    [(None, 1.0), (-1.0, 1.0), (1.0, None), (1.0, -0.1), (0.0, 0.0)],
)
def test_recommendation_requires_positive_amount_and_percentage(monto, porcentaje):
    assert not es_recomendacion_util(monto, porcentaje)


def test_recommendation_with_non_positive_savings_requires_explicit_reason():
    assert es_recomendacion_util(None, -1, "Necesaria para cumplir el protocolo HACCP")
    assert not es_recomendacion_util(None, -1, "Sin justificación")


def test_recommendation_text_is_user_friendly():
    title, rationale = generar_textos_recomendacion(
        accion="apagar",
        equipo="camaras_2_y_3",
        horas=2,
        ventana=["18:00", "22:00"],
        monto=1450,
        porcentaje=1.72,
    )

    assert title == "Apagar Cámaras 2 y 3"
    assert "18:00 a 22:00" in rationale
    assert "$1.450 CLP" in rationale
    assert "1,72%" in rationale
