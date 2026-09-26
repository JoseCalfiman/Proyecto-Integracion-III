from types import SimpleNamespace

from haccp_validator import (
    DEFAULT_HACCP_RULE,
    evaluate_temperature_rule,
    evaluate_temperature_series,
    validar_haccp,
)


def test_single_temperature_below_threshold_is_ok():
    result = evaluate_temperature_rule(temperature_c=3.5, duration_seconds=120)
    assert result["is_alert"] is False
    assert result["severity"] == "normal"


def test_default_rule_uses_four_degrees_and_fifteen_minutes():
    before_tolerance = evaluate_temperature_rule(temperature_c=4.1, duration_seconds=899)
    at_tolerance = evaluate_temperature_rule(temperature_c=4.1, duration_seconds=900)

    assert DEFAULT_HACCP_RULE["max_temp_c"] == 4.0
    assert DEFAULT_HACCP_RULE["warning_duration_seconds"] == 900
    assert before_tolerance["is_alert"] is False
    assert at_tolerance["is_alert"] is True
    assert at_tolerance["severity"] == "warning"
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
    result = evaluate_temperature_rule(temperature_c=6.0, duration_seconds=900)
    assert result["is_alert"] is True
    assert result["severity"] == "critical"
    assert "4.0" in result["message"]


def test_temperature_below_absolute_minimum_triggers_after_tolerance():
    at_minimum = evaluate_temperature_rule(temperature_c=-30.0, duration_seconds=900)
    below_minimum = evaluate_temperature_rule(temperature_c=-30.1, duration_seconds=900)

    assert at_minimum["is_alert"] is False
    assert below_minimum["is_alert"] is True
    assert below_minimum["severity"] == "warning"


def test_database_rule_is_mapped_to_validator_thresholds():
    rule = SimpleNamespace(
        max_absolute_temp=5.0,
        min_absolute_temp=-20.0,
        tolerance_time_min=2,
    )

    result = validar_haccp({"temperature_c": 5.1, "duration_seconds": 120}, rule)

    assert result["is_alert"] is True
    assert result["severity"] == "warning"
    assert result["threshold_c"] == 5.0
    assert result["rule"]["min_temp_c"] == -20.0


def test_validator_rule_dictionary_keeps_duration_in_seconds():
    result = validar_haccp(
        {"temperature_c": 4.1, "duration_seconds": 120},
        {"max_temp_c": 4.0, "min_temp_c": -30.0, "warning_duration_seconds": 120},
    )

    assert result["is_alert"] is True
    assert result["rule"]["warning_duration_seconds"] == 120


def test_event_without_measurement_or_duration_is_not_validated():
    result = validar_haccp({"severity": "critical"}, SimpleNamespace())

    assert result["is_alert"] is False
    assert result["severity"] == "normal"
    assert "temperature_c" in result["message"]


def test_temperature_series_detects_drift_window():
    series = [2.0, 3.5] + [5.0] * 89
    result = evaluate_temperature_series(series, sample_interval_seconds=10)
    assert result["has_violation"] is True
    assert result["total_violation_seconds"] >= 900
    assert result["rule"]["max_temp_c"] == DEFAULT_HACCP_RULE["max_temp_c"]
