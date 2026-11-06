import pytest

from descriptive_stats import calcular_estadisticas, detectar_atipicos


@pytest.mark.parametrize(
    ("muestras", "esperado"),
    [
        ([-18] * 4, (4, -18, -18, 0, -18, -18, -18, -18, 0)),
        ([-18, -17, -16], (3, -17, -17, 1, -18, -16, -17.5, -16.5, 1)),
        ([4, 0, 4, 0], (4, 2, 2, (16 / 3) ** 0.5, 0, 4, 0, 4, 4)),
        ([0, 0, 0, 0, 10], (5, 2, 0, 20 ** 0.5, 0, 10, 0, 0, 0)),
    ],
)
def test_estadisticas_de_ventanas_controladas(muestras, esperado):
    claves = ("sample_count", "media", "mediana", "std", "min", "max", "q1", "q3", "iqr")
    assert calcular_estadisticas(muestras) == pytest.approx(dict(zip(claves, esperado)))


def test_ventanas_vacia_y_unitaria():
    vacia = calcular_estadisticas([])
    assert vacia["sample_count"] == 0
    assert all(valor is None for clave, valor in vacia.items() if clave != "sample_count")
    assert calcular_estadisticas([-18])["std"] is None
    assert calcular_estadisticas([-18])["iqr"] == 0


@pytest.mark.parametrize(
    ("muestras", "indices"),
    [
        ([-18, -18.1, -17.9, -18, 20], [4]),
        ([-18, -18.1, -17.9, -18, -17.8], []),
        ([-30, -18, -18, -18, -18, 20], [0, 5]),
    ],
)
def test_detectar_atipicos_conserva_posiciones_originales(muestras, indices):
    assert detectar_atipicos(muestras) == indices
