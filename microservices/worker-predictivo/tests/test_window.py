from collections import deque
from datetime import datetime, timedelta, timezone

from window import actualizar_ventana

T0 = datetime(2026, 10, 13, 14, 0, 0, tzinfo=timezone.utc)


def _ventana(maxlen=30):
    return deque(maxlen=maxlen)


def test_descarta_lecturas_fuera_de_los_5_minutos():
    buf = _ventana()
    for i in range(0, 12):  # una lectura cada 60 s durante 11 min
        actualizar_ventana(buf, T0 + timedelta(minutes=i), -18.0 + i * 0.1, 5)
    tiempos = [d["timestamp"] for d in buf]
    assert tiempos[-1] == T0 + timedelta(minutes=11)
    assert tiempos[0] == T0 + timedelta(minutes=6)  # 11 - 5
    assert len(buf) == 6


def test_respeta_el_maximo_de_mediciones():
    buf = _ventana(maxlen=30)
    for i in range(100):  # una cada 1 s => cabrían 100 en 5 min
        actualizar_ventana(buf, T0 + timedelta(seconds=i), -18.0, 5)
    assert len(buf) == 30
    assert buf[-1]["timestamp"] == T0 + timedelta(seconds=99)


def test_ignora_duplicados_y_desordenados():
    buf = _ventana()
    assert actualizar_ventana(buf, T0 + timedelta(seconds=10), -18.0, 5) is True
    assert actualizar_ventana(buf, T0 + timedelta(seconds=10), -17.0, 5) is False  # repetida
    assert actualizar_ventana(buf, T0 + timedelta(seconds=5), -17.0, 5) is False   # desordenada
    assert len(buf) == 1


def test_reloj_del_sensor_que_retrocede_mucho_reinicia_la_ventana():
    buf = _ventana()
    for i in range(5):
        actualizar_ventana(buf, T0 + timedelta(minutes=i), -18.0, 5)
    assert actualizar_ventana(buf, T0 - timedelta(hours=1), -18.0, 5) is True
    assert len(buf) == 1


def test_ventana_vacia_acepta_cualquier_lectura():
    buf = _ventana()
    assert actualizar_ventana(buf, T0, -18.0, 5) is True
    assert len(buf) == 1
