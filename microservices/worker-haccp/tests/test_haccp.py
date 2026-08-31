from haccp_validator import (
    DEFAULT_HACCP_RULE,
    evaluate_temperature_rule,
    evaluate_temperature_series,
)


def test_single_temperature_below_threshold_is_ok():
    result = evaluate_temperature_rule(temperature_c=3.5, duration_seconds=120)
    assert result["is_alert"] is False
    assert result["severity"] == "normal"


def test_single_temperature_above_threshold_for_too_long_triggers_alert():
    result = evaluate_temperature_rule(temperature_c=6.0, duration_seconds=180)
    assert result["is_alert"] is True
    assert result["severity"] == "critical"
    assert "4.0°C" in result["message"]


def test_temperature_series_detects_drift_window():
    series = [2.0, 3.5, 5.0, 5.5, 6.0, 6.2, 6.0, 6.5, 6.8, 7.0, 7.1, 6.9, 6.7]
    result = evaluate_temperature_series(series, sample_interval_seconds=10)
    assert result["has_violation"] is True
    assert result["total_violation_seconds"] >= 120
    assert result["rule"]["max_temp_c"] == DEFAULT_HACCP_RULE["max_temp_c"]
