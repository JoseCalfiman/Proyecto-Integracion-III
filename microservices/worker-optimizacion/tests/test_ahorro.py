import pytest

from ahorro import Action, calcular_ahorro_action, calcular_ahorro_potencial


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
