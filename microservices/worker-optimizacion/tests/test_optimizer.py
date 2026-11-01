import pandas as pd

from buffer import ReadingsBuffer, normalize_reading
from optimizer import (
    build_example_df,
    forecast_daily_consumption,
    forecast_example,
    prepare_prophet_history,
)


def test_build_example_df_has_ds_and_y_columns():
    df = build_example_df()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["ds", "y"]
    assert len(df) == 120


def test_build_example_df_dtypes():
    df = build_example_df(periods=30, start="2024-06-01")
    assert pd.api.types.is_datetime64_any_dtype(df["ds"])
    assert pd.api.types.is_float_dtype(df["y"])
    assert df["ds"].iloc[0] == pd.Timestamp("2024-06-01")


def test_build_example_df_is_reproducible_with_seed():
    df1 = build_example_df(seed=123)
    df2 = build_example_df(seed=123)
    pd.testing.assert_frame_equal(df1, df2)


def test_forecast_example_returns_expected_columns():
    _, forecast = forecast_example(periods=60, horizon=7)
    assert "ds" in forecast.columns
    assert "yhat" in forecast.columns
    assert "yhat_lower" in forecast.columns
    assert "yhat_upper" in forecast.columns
    assert len(forecast) == 60 + 7


def _daily_kwh_buffer() -> ReadingsBuffer:
    buf = ReadingsBuffer()
    for day in range(1, 15):
        date = f"2024-01-{day:02d}"
        buf.add(normalize_reading({"ts": f"{date}T08:00:00Z", "consumption_kwh": 10.0}))
        buf.add(normalize_reading({"ts": f"{date}T18:00:00Z", "consumption_kwh": 2.5}))
    return buf


def test_prepare_prophet_history_builds_ds_y_from_daily_kwh():
    history = prepare_prophet_history(_daily_kwh_buffer().to_dataframe())

    assert history is not None
    assert list(history.columns) == ["ds", "y"]
    assert len(history) == 14
    assert history["y"].tolist() == [12.5] * 14
    assert history["ds"].iloc[0] == pd.Timestamp("2024-01-01")
    assert history["ds"].iloc[-1] == pd.Timestamp("2024-01-14")
    assert history["ds"].is_monotonic_increasing


def test_prepare_prophet_history_returns_none_when_data_is_missing():
    assert prepare_prophet_history(None) is None
    assert prepare_prophet_history(pd.DataFrame(columns=["ds", "y"])) is None
    assert prepare_prophet_history(pd.DataFrame({"foo": [1]})) is None
    one_day = pd.DataFrame({"ds": [pd.Timestamp("2024-01-01")], "y": [4.0]})
    assert prepare_prophet_history(one_day) is None
    missing = pd.DataFrame({"ds": [pd.NaT, "2024-01-02"], "y": [1.0, None]})
    assert prepare_prophet_history(missing) is None


def test_prophet_receives_daily_history_and_forecasts_next_day(monkeypatch):
    from prophet import Prophet as RealProphet

    captured = {}

    class SpyProphet(RealProphet):
        def fit(self, df, **kwargs):
            captured["history"] = df.copy()
            return super().fit(df, **kwargs)

    monkeypatch.setattr("prophet.Prophet", SpyProphet)

    history = prepare_prophet_history(_daily_kwh_buffer().to_dataframe())
    forecast = forecast_daily_consumption(history, horizon=1)

    assert "history" in captured
    assert list(captured["history"].columns) == ["ds", "y"]
    pd.testing.assert_frame_equal(
        captured["history"].reset_index(drop=True),
        history.reset_index(drop=True),
    )
    assert forecast is not None
    assert {"ds", "yhat", "yhat_lower", "yhat_upper"} <= set(forecast.columns)
    assert len(forecast) == len(history) + 1
    assert pd.Timestamp(forecast["ds"].iloc[-1]) == pd.Timestamp("2024-01-15")
    assert pd.notna(forecast["yhat"].iloc[-1])


def test_forecast_daily_consumption_does_not_invent_prediction_without_data():
    assert forecast_daily_consumption(pd.DataFrame(columns=["ds", "y"])) is None
    assert forecast_daily_consumption(
        pd.DataFrame({"ds": [pd.Timestamp("2024-01-01")], "y": [9.0]})
    ) is None
