import pandas as pd

from optimizer import build_example_df, forecast_example


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
