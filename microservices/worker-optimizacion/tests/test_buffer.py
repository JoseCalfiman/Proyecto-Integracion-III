import pandas as pd

from buffer import ReadingsBuffer, normalize_reading


def test_normalize_reading_maps_aliases():
    reading = normalize_reading(
        {"ts": "2024-01-01T00:00:00Z", "consumo": "12.5", "temperatura": 3.2}
    )
    assert reading["consumption_kwh"] == 12.5
    assert reading["temperature"] == 3.2
    assert reading["ts"].year == 2024


def test_normalize_reading_without_useful_data_returns_none():
    assert normalize_reading({"foo": "bar"}) is None
    assert normalize_reading("not-a-dict") is None


def test_buffer_to_dataframe_aggregates_consumption_by_day():
    buf = ReadingsBuffer()
    buf.add(normalize_reading({"ts": "2024-01-01T10:00:00Z", "consumption_kwh": 1.0}))
    buf.add(normalize_reading({"ts": "2024-01-01T20:00:00Z", "consumption_kwh": 2.0}))
    buf.add(normalize_reading({"ts": "2024-01-02T10:00:00Z", "consumption_kwh": 4.0}))

    df = buf.to_dataframe()

    assert list(df.columns) == ["ds", "y"]
    assert len(df) == 2
    assert df["y"].tolist() == [3.0, 4.0]
    assert df["ds"].iloc[0] == pd.Timestamp("2024-01-01")


def test_buffer_ignores_readings_without_consumption():
    buf = ReadingsBuffer()
    buf.add(normalize_reading({"ts": "2024-01-01T10:00:00Z", "temperature": 3.0}))
    assert buf.to_dataframe().empty


def test_missing_timestamp_is_not_invented_into_history():
    assert normalize_reading({"consumption_kwh": 5.0}) is None
    assert normalize_reading({"ts": " ", "kwh": 5.0}) is None
    assert normalize_reading({"timestamp": "no-es-fecha", "kwh": 5.0}) is None


def test_normalize_reading_accepts_sensor_raw_consumption_kw():
    reading = normalize_reading(
        {
            "timestamp": "2024-01-01T00:00:00Z",
            "id_chamber": "66666666-6666-6666-6666-666666666666",
            "consumption_kw": 3.6,
            "temperature": 2.5,
        }
    )

    assert reading["consumption_kw"] == 3.6
    assert reading["consumption_kwh"] is None
    assert reading["id_chamber"] == "66666666-6666-6666-6666-666666666666"


def test_buffer_integrates_consumption_kw_using_real_time_delta():
    buf = ReadingsBuffer()
    chamber = "66666666-6666-6666-6666-666666666666"

    for ts in (
        "2024-01-01T00:00:00Z",
        "2024-01-01T00:00:10Z",
        "2024-01-01T00:00:20Z",
    ):
        buf.add(
            normalize_reading(
                {
                    "timestamp": ts,
                    "id_chamber": chamber,
                    "consumption_kw": 3.6,
                }
            )
        )

    df = buf.to_dataframe()

    # Dos intervalos de 10 s a 3.6 kW = 0.02 kWh.
    assert len(df) == 1
    assert abs(df["y"].iloc[0] - 0.02) < 1e-9


def test_buffer_caps_power_interval_at_five_minutes():
    buf = ReadingsBuffer()
    chamber = "66666666-6666-6666-6666-666666666666"
    buf.add(
        normalize_reading(
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "id_chamber": chamber,
                "consumption_kw": 3.6,
            }
        )
    )
    buf.add(
        normalize_reading(
            {
                "timestamp": "2024-01-01T01:00:00Z",
                "id_chamber": chamber,
                "consumption_kw": 3.6,
            }
        )
    )

    df = buf.to_dataframe()

    # 3.6 kW * 300 s / 3600 = 0.3 kWh; no se contabiliza una hora completa.
    assert abs(df["y"].iloc[0] - 0.3) < 1e-9
