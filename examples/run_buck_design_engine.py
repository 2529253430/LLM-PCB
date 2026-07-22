from __future__ import annotations

import json
from pathlib import Path

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)


def main() -> None:
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        inductor_ripple_ratio=0.30,
        output_voltage_ripple_v=0.05,
        input_voltage_ripple_v=0.20,
        feedback_bottom_resistance_ohm=10_000.0,
        capacitor_derating_ratio=0.50,
    )

    selected_ic = BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        minimum_on_time_s=80e-9,
        maximum_duty_cycle=0.90,
        switch_current_limit_a=5.5,
        synchronous_rectification=True,
    )

    result = BuckDesignEngine().design(
        design_input,
        selected_ic,
    )

    output_path = Path("output/buck_design_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Selected IC: {result.part_number}")
    print(
        "Recommended inductor: "
        f"{result.recommended_inductance_h * 1e6:.2f} uH"
    )
    print(
        "Recommended inductor current rating: "
        f"{result.recommended_inductor_current_rating_a:.2f} A"
    )
    print(
        "Recommended input capacitance: "
        f"{result.recommended_input_capacitance_f * 1e6:.2f} uF"
    )
    print(
        "Recommended output capacitance: "
        f"{result.recommended_output_capacitance_f * 1e6:.2f} uF"
    )
    print(
        "Feedback divider: "
        f"Rtop={result.feedback_top_resistance_ohm:.1f} ohm, "
        f"Rbottom={result.feedback_bottom_resistance_ohm:.1f} ohm"
    )
    print(f"Result written to: {output_path.resolve()}")

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
