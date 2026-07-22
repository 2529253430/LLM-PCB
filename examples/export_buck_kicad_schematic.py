from __future__ import annotations

from pathlib import Path

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.export.kicad_schematic_exporter import (
    KiCadSchematicExporter,
)
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


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

    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    output_path = Path(
        "output/Buck_24V_to_5V_3A.kicad_sch"
    )

    exported = KiCadSchematicExporter().export(
        design=schematic,
        layout=layout,
        output_path=output_path,
    )

    print(
        "Modern KiCad schematic written to: "
        f"{exported.resolve()}"
    )
    print(f"Symbols: {len(layout.symbols)}")
    print(f"Wires: {len(layout.wires)}")
    print(f"Junctions: {len(layout.junctions)}")
    print(f"Labels: {len(layout.labels)}")
    print(
        "Open the file directly in KiCad 10 "
        "Schematic Editor."
    )


if __name__ == "__main__":
    main()
