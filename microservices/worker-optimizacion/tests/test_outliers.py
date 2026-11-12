import pandas as pd
import pytest

from outliers import mark_consumption_outliers, outlier_records


def _series(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ds": pd.date_range("2026-01-01", periods=len(values), freq="D"),
            "y": values,
        }
    )


def test_spike_is_marked_and_original_value_is_preserved():
    source = _series([80.0] * 13 + [100_000.0])
    snapshot = source.copy()

    mark = mark_consumption_outliers(source)

    pd.testing.assert_frame_equal(source, snapshot)
    assert mark.q1 == 80.0
    assert mark.q3 == 80.0
    assert mark.iqr == 0.0
    assert mark.frame["is_outlier"].tolist() == [False] * 13 + [True]
    assert mark.frame["y"].iloc[-1] == 100_000.0
    assert mark.frame["y_original"].iloc[-1] == 100_000.0
    assert pd.isna(mark.frame["y_clean"].iloc[-1])
    assert mark.frame.loc[~mark.frame["is_outlier"], "y_clean"].tolist() == [80.0] * 13
    assert outlier_records(mark) == [
        {"ds": "2026-01-14T00:00:00", "y_original": 100_000.0}
    ]


def test_seven_day_window_marks_isolated_spike():
    mark = mark_consumption_outliers(_series([80.0] * 6 + [100_000.0]))

    assert mark.frame["is_outlier"].tolist() == [False] * 6 + [True]
    assert mark.frame["y_original"].iloc[-1] == 100_000.0
    assert pd.isna(mark.frame["y_clean"].iloc[-1])


def test_normal_series_is_not_marked_and_keeps_forecast_values():
    values = [78.0, 79.0, 80.0, 81.0, 82.0, 80.0, 79.5, 81.5]
    mark = mark_consumption_outliers(_series(values))

    assert not mark.frame["is_outlier"].any()
    assert mark.frame["y_clean"].tolist() == values
    assert mark.frame["y_original"].tolist() == values
    assert outlier_records(mark) == []


def test_low_isolated_spike_is_marked():
    mark = mark_consumption_outliers(_series([80.0] * 6 + [0.0]))

    assert bool(mark.frame["is_outlier"].iloc[-1])
    assert mark.frame["y_original"].iloc[-1] == 0.0


def test_short_series_is_not_flagged():
    mark = mark_consumption_outliers(_series([80.0, 80.0, 100_000.0]))

    assert mark.q1 is None
    assert not mark.frame["is_outlier"].any()
    assert mark.frame["y_clean"].tolist() == [80.0, 80.0, 100_000.0]


def test_mark_requires_value_column_and_non_negative_k():
    with pytest.raises(ValueError, match="columna"):
        mark_consumption_outliers(pd.DataFrame({"ds": [1]}))
    with pytest.raises(ValueError, match="k debe"):
        mark_consumption_outliers(_series([80.0] * 4), k=-1)
