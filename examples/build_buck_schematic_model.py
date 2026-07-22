from __future__ import annotations

import json
from pathlib import Path

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.schematic.buck_builder import BuckSchematicBuilder


def main() -> None:
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        output_voltage_ripple_v=0.05,
        input_voltage_ripple_v=0.20,
    )

    selected_ic = BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        minimum_on_time_s=80e-9,
        maximum_duty_cycle=0.90,
        switch_current_limit_a=5.5,
    )

    design_result = BuckDesignEngine().design(
        design_input,
        selected_ic,
    )

    schematic = BuckSchematicBuilder().build(
        design_input,
        selected_ic,
        design_result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )

    output_path = Path("output/buck_schematic_model.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            schematic.to_dict(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Schematic: {schematic.name}")
    print(f"Components: {len(schematic.components)}")
    print(f"Nets: {len(schematic.nets)}")
    print("Component references:")
    for component in schematic.components:
        print(
            f"- {component.reference}: "
            f"{component.value}"
        )

    print("Nets:")
    for net in schematic.nets:
        endpoints = ", ".join(
            f"{connection.component_reference}."
            f"{connection.pin_number}"
            for connection in net.connections
        )
        print(f"- {net.name}: {endpoints}")

    print(f"Result written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
