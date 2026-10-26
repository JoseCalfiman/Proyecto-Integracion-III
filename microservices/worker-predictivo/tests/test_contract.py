from datetime import datetime, timezone

import pytest

from contract import ContractError, parse_sensor_reading, parse_timestamp

CHAMBER = "44444444-4444-4444-4444-444444444444"


def _msg(**over):
    base = {
        "id_chamber": CHAMBER,
        "timestamp": "2026-10-13T14:30:00Z",
        "temperature": -17.4,
        "consumption_kw": 1.25,
    }
    base.update(over)
    return base


def test_mensaje_valido():
    r = parse_sensor_reading(_msg())
    assert r.id_chamber == CHAMBER
    assert r.temperature == -17.4
    assert r.consumption_kw == 1.25
    assert r.timestamp == datetime(2026, 10, 13, 14, 30, tzinfo=timezone.utc)


def test_consumption_kw_es_opcional():
    msg = _msg()
    del msg["consumption_kw"]
    assert parse_sensor_reading(msg).consumption_kw is None


def test_consumption_kw_invalido_no_descarta_la_lectura():
    assert parse_sensor_reading(_msg(consumption_kw="abc")).consumption_kw is None


def test_alias_chamber_id_y_recorded_at():
    # Nombres que usa el propio ejemplo de kafka_producer.py de Ingesta
    msg = {
        "chamber_id": CHAMBER,
        "temperature": -18.5,
        "consumption_kw": 2.34,
        "recorded_at": "2026-09-28T21:00:00+00:00",
    }
    r = parse_sensor_reading(msg)
    assert r.id_chamber == CHAMBER
    assert r.timestamp == datetime(2026, 9, 28, 21, 0, tzinfo=timezone.utc)


def test_nombres_canonicos_ganan_sobre_los_alias():
    otro = "55555555-5555-5555-5555-555555555555"
    r = parse_sensor_reading(_msg(chamber_id=otro, recorded_at="2020-01-01T00:00:00Z"))
    assert r.id_chamber == CHAMBER
    assert r.timestamp == datetime(2026, 10, 13, 14, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize("campo", ["id_chamber", "timestamp", "temperature"])
def test_campos_obligatorios(campo):
    msg = _msg()
    del msg[campo]
    with pytest.raises(ContractError):
        parse_sensor_reading(msg)


@pytest.mark.parametrize("valor", ["FRIDGE_001", "123", "", 5])
def test_id_chamber_debe_ser_uuid(valor):
    with pytest.raises(ContractError):
        parse_sensor_reading(_msg(id_chamber=valor))


@pytest.mark.parametrize("valor", [-50.1, 50.1, 999, -273])
def test_temperatura_fuera_del_rango_de_ingesta(valor):
    with pytest.raises(ContractError):
        parse_sensor_reading(_msg(temperature=valor))


@pytest.mark.parametrize("valor", [-50, 50, 0])
def test_temperatura_en_los_limites(valor):
    assert parse_sensor_reading(_msg(temperature=valor)).temperature == valor


def test_timestamp_epoch_como_texto():
    assert parse_timestamp("1760366400") == parse_timestamp(1_760_366_400)


@pytest.mark.parametrize("valor", [None, True, "caliente", float("nan"), float("inf")])
def test_temperatura_invalida(valor):
    with pytest.raises(ContractError):
        parse_sensor_reading(_msg(temperature=valor))


def test_no_es_un_objeto():
    with pytest.raises(ContractError):
        parse_sensor_reading([1, 2, 3])


def test_timestamp_iso_con_y_sin_zona():
    con_z = parse_timestamp("2026-10-13T14:30:00Z")
    con_offset = parse_timestamp("2026-10-13T11:30:00-03:00")
    sin_zona = parse_timestamp("2026-10-13T14:30:00")
    assert con_z == con_offset == sin_zona
    assert con_z.tzinfo is not None


def test_timestamp_epoch_segundos_y_milisegundos():
    seg = parse_timestamp(1_760_366_400)
    ms = parse_timestamp(1_760_366_400_000)
    assert seg == ms
    assert seg.tzinfo is not None


def test_mezclar_iso_y_epoch_no_rompe_la_comparacion():
    # Bug original: fromtimestamp() devolvía datetime sin zona y comparar con
    # uno con zona lanzaba TypeError.
    a = parse_timestamp("2026-10-13T14:30:00Z")
    b = parse_timestamp(1_760_366_460)
    assert (b - a).total_seconds() != 0


@pytest.mark.parametrize("valor", [None, True, "ayer", [], {}])
def test_timestamp_invalido(valor):
    with pytest.raises(ContractError):
        parse_timestamp(valor)
