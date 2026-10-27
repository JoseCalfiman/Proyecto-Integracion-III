"""El consumer valida el contrato de sensor.raw sin Kafka ni base de datos reales."""
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

kc = pytest.importorskip("kafka_consumer")

CHAMBER = "44444444-4444-4444-4444-444444444444"
T0 = datetime(2026, 10, 13, 14, 0, 0, tzinfo=timezone.utc)


class FakeMsg:
    def __init__(self, payload, raw=None):
        self._v = raw if raw is not None else json.dumps(payload).encode()

    def value(self):
        return self._v

    def topic(self):
        return "sensor.raw"

    def partition(self):
        return 0


@pytest.fixture
def worker(monkeypatch):
    guardadas, alertas = [], []

    monkeypatch.setattr(kc, "Consumer", lambda conf: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(kc, "Producer", lambda conf: SimpleNamespace())

    @contextmanager
    def fake_session():
        yield SimpleNamespace(rollback=lambda: None)

    monkeypatch.setattr(kc, "get_session", fake_session)
    monkeypatch.setattr(
        kc, "obtener_regla_haccp_activa",
        lambda session, chamber_id: {"max_absolute_temp": -10.0, "tolerance_time_min": 40.0, "severity": "high"},
    )
    monkeypatch.setattr(kc, "guardar_prediccion", lambda session, **kw: guardadas.append(kw))

    w = kc.PredictiveKafkaWorker()
    monkeypatch.setattr(w, "send_anomaly_alert", lambda payload: alertas.append(payload))
    w.guardadas, w.alertas = guardadas, alertas
    return w


def _lectura(i, temp):
    return {
        "id_chamber": CHAMBER,
        "timestamp": (T0 + timedelta(minutes=i)).isoformat().replace("+00:00", "Z"),
        "temperature": temp,
        "consumption_kw": 1.0,
    }


def test_lectura_valida_se_procesa(worker):
    worker._procesar_mensaje(FakeMsg(_lectura(0, -18.0)))
    assert len(worker.guardadas) == 1
    assert worker.guardadas[0]["chamber_id"] == CHAMBER


@pytest.mark.parametrize(
    "raw",
    [b"esto no es json", b"[1,2]", b'{"fridge_id": "FRIDGE_001", "temperature": 5}', b"\xff\xfe"],
)
def test_mensajes_invalidos_se_descartan_sin_excepcion(worker, raw):
    worker._procesar_mensaje(FakeMsg(None, raw=raw))
    assert worker.guardadas == [] and worker.alertas == []


def test_timestamp_epoch_y_iso_en_la_misma_camara(worker):
    worker._procesar_mensaje(FakeMsg(_lectura(0, -18.0)))
    epoch = {**_lectura(1, -17.5), "timestamp": (T0 + timedelta(minutes=1)).timestamp()}
    worker._procesar_mensaje(FakeMsg(epoch))  # antes lanzaba TypeError
    assert len(worker.guardadas) == 2


def test_lectura_repetida_se_ignora(worker):
    worker._procesar_mensaje(FakeMsg(_lectura(0, -18.0)))
    n = len(worker.guardadas)
    worker._procesar_mensaje(FakeMsg(_lectura(0, -18.0)))
    assert len(worker.guardadas) == n


def test_lectura_desordenada_se_ignora(worker):
    worker._procesar_mensaje(FakeMsg(_lectura(5, -18.0)))
    n = len(worker.guardadas)
    worker._procesar_mensaje(FakeMsg(_lectura(2, -17.0)))
    assert len(worker.guardadas) == n
