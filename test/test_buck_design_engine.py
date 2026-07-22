from __future__ import annotations

import pytest

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignError,
    BuckDesignInput,
    BuckICParameters,
)


def _design_input() -> BuckDesignInput:
    return BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        inductor_ripple_ratio=0.30,
        output_voltage_ripple_v=0.05,
        input_voltage_ripple_v=0.20,
        feedback_bottom_resistance_ohm=10_000.0,
    )


def _ic() -> BuckICParameters:
    return BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        minimum_on_time_s=80e-9,
        maximum_duty_cycle=0.90,
        switch_current_limit_a=5.5,
        synchronous_rectification=True,
    )


def test_engine_calculates_complete_design() -> None:
    result = BuckDesignEngine().design(
        _design_input(),
        _ic(),
    )

    assert result.part_number == "EX36S4"
    assert 0 < result.duty_cycle_at_max_input < 1
    assert 0 < result.duty_cycle_at_min_input < 1
    assert result.recommended_inductance_h >= (
        result.calculated_inductance_h
    )
    assert result.inductor_peak_current_a > 3.0
    assert result.recommended_output_capacitance_f > 0
    assert result.recommended_input_capacitance_f > 0
    assert result.feedback_top_resistance_ohm > 0
    assert result.calculated_output_voltage_v == pytest.approx(5.0)
    assert result.estimated_output_power_w == pytest.approx(15.0)


def test_feedback_resistors_match_target_voltage() -> None:
    result = BuckDesignEngine().design(
        _design_input(),
        _ic(),
    )

    assert result.feedback_bottom_resistance_ohm == 10_000.0
    assert result.feedback_top_resistance_ohm == pytest.approx(
        52_500.0
    )


def test_peak_current_respects_switch_limit() -> None:
    result = BuckDesignEngine().design(
        _design_input(),
        _ic(),
    )

    assert result.inductor_peak_current_a < 5.5
    assert not any(
        "限流值" in warning
        for warning in result.warnings
    )


def test_invalid_buck_voltage_is_rejected() -> None:
    invalid = BuckDesignInput(
        input_voltage_min_v=5.0,
        input_voltage_max_v=12.0,
        output_voltage_v=5.0,
        output_current_a=1.0,
    )

    with pytest.raises(BuckDesignError):
        BuckDesignEngine().design(invalid, _ic())


def test_duty_cycle_limit_is_checked() -> None:
    ic = BuckICParameters(
        part_number="LIMITED",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        maximum_duty_cycle=0.20,
    )

    with pytest.raises(
        BuckDesignError,
        match="duty cycle",
    ):
        BuckDesignEngine().design(_design_input(), ic)


def test_output_esr_can_exceed_ripple_budget() -> None:
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        output_voltage_ripple_v=0.01,
        output_capacitor_esr_ohm=0.1,
    )

    with pytest.raises(
        BuckDesignError,
        match="ESR",
    ):
        BuckDesignEngine().design(design_input, _ic())


def test_result_can_be_serialized() -> None:
    result = BuckDesignEngine().design(
        _design_input(),
        _ic(),
    )

    payload = result.to_dict()

    assert payload["part_number"] == "EX36S4"
    assert payload["recommended_inductance_h"] > 0
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["assumptions"], list)
