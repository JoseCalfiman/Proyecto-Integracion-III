from haccp_validator import (
    DEFAULT_HACCP_RULE,
    evaluate_temperature_rule,
    evaluate_temperature_series,
)


def test_single_temperature_below_threshold_is_ok():
    result = evaluate_temperature_rule(temperature_c=3.5, duration_seconds=120)
    assert result["is_alert"] is False
    assert result["severity"] == "normal"


def test_default_rule_uses_four_degrees_and_ten_minutes():
    before_tolerance = evaluate_temperature_rule(temperature_c=4.1, duration_seconds=599)
    at_tolerance = evaluate_temperature_rule(temperature_c=4.1, duration_seconds=600)

    assert DEFAULT_HACCP_RULE["max_temp_c"] == 4.0
    assert DEFAULT_HACCP_RULE["warning_duration_seconds"] == 600
    assert before_tolerance["is_alert"] is False
    assert at_tolerance["is_alert"] is True
    assert at_tolerance["rule"]["max_temp_c"] == 4.0


def test_camera_rule_overrides_generic_defaults():
    result = evaluate_temperature_rule(
        temperature_c=5.1,
        duration_seconds=60,
        rule={"max_temp_c": 5.0, "warning_duration_seconds": 30},
    )

    assert result["is_alert"] is True
    assert result["threshold_c"] == 5.0


def test_single_temperature_above_threshold_for_too_long_triggers_alert():
    result = evaluate_temperature_rule(temperature_c=6.0, duration_seconds=600)
    assert result["is_alert"] is True
    assert result["severity"] == "critical"
    assert "4.0°C" in result["message"]


def test_temperature_series_detects_drift_window():
    series = [2.0, 3.5] + [5.0] * 59
    result = evaluate_temperature_series(series, sample_interval_seconds=10)
    assert result["has_violation"] is True
    assert result["total_violation_seconds"] >= 600
    assert result["rule"]["max_temp_c"] == DEFAULT_HACCP_RULE["max_temp_c"]
