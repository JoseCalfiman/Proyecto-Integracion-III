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
