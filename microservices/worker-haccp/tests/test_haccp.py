from types import SimpleNamespace

import pytest

from haccp_validator import (
    DEFAULT_HACCP_RULE,
    HaccpRuleConfigurationError,
    evaluate_predictive_event,
    evaluate_temperature_rule,
    evaluate_temperature_series,
    validar_haccp,
)


PREDICTIVE_EVENT = {"temperature": 2.0, "remaining_time_min": 20.0}
ACTIVE_RULE = {
    "min_absolute_temp": -20.0,
    "max_absolute_temp": 5.0,
    "tolerance_time_min": 15,
}


@pytest.mark.parametrize(
    ("payload", "expected_violation"),
    [
        ({"temperature": -20.1, "remaining_time_min": 20}, "temperature_below_minimum"),
        ({"temperature": 5.1, "remaining_time_min": 20}, "temperature_above_maximum"),
        ({"temperature": -20, "remaining_time_min": 20}, None),
        ({"temperature": 5, "remaining_time_min": 20}, None),
        ({"temperature": 2, "remaining_time_min": 14}, "remaining_time_within_tolerance"),
        ({"temperature": 2, "remaining_time_min": 15}, "remaining_time_within_tolerance"),
        ({"temperature": 2, "remaining_time_min": 16}, None),
        ({"temperature": 2, "remaining_time_min": 20}, None),
    ],
)
def test_predictive_event_decision_boundaries(payload, expected_violation):
    result = evaluate_predictive_event(payload, ACTIVE_RULE)

    assert result["is_alert"] is (expected_violation is not None)
    if expected_violation:
        assert result["violations"] == [expected_violation]
    else:
        assert result["violations"] == []


def test_predictive_event_combines_simultaneous_violations_once():
    result = evaluate_predictive_event(
        {"temperature": 6, "remaining_time_min": 10},
        ACTIVE_RULE,
    )

    assert result["is_alert"] is True
    assert result["violations"] == [
        "temperature_above_maximum",
        "remaining_time_within_tolerance",
    ]


@pytest.mark.parametrize(
    "rule_overrides",
    [
        {"min_absolute_temp": None},
        {"max_absolute_temp": None},
        {"tolerance_time_min": None},
        {"min_absolute_temp": float("-inf")},
        {"max_absolute_temp": float("nan")},
        {"max_absolute_temp": float("inf")},
        {"tolerance_time_min": float("nan")},
        {"tolerance_time_min": -1},
        {"min_absolute_temp": 6, "max_absolute_temp": 5},
        {"max_absolute_temp": "5"},
        {"tolerance_time_min": True},
    ],
)
def test_predictive_event_rejects_invalid_active_rule(rule_overrides):
    rule = {**ACTIVE_RULE, **rule_overrides}

    with pytest.raises(HaccpRuleConfigurationError):
        evaluate_predictive_event(PREDICTIVE_EVENT, rule)


@pytest.mark.parametrize(
    "payload",
    [
        {"temperature": float("nan"), "remaining_time_min": 1},
        {"temperature": 1, "remaining_time_min": float("inf")},
        {"temperature": True, "remaining_time_min": 1},
        {"temperature": 1, "remaining_time_min": -1},
    ],
)
def test_predictive_event_rejects_non_numeric_or_non_finite_values(payload):
    with pytest.raises(ValueError):
        evaluate_predictive_event(payload, ACTIVE_RULE)


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
