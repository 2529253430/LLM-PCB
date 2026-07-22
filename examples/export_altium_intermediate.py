from __future__ import annotations

from src.design.buck_engine import BuckDesignEngine, BuckDesignInput, BuckICParameters
from src.export import ExportRequest, export_design
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def main() -> None:
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
    )
    selected_ic = BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        minimum_on_time_s=80e-9,
        maximum_duty_cycle=0.90,
        switch_current_limit_a=5.5,
    )
    design_result = BuckDesignEngine().design(design_input, selected_ic)
    schematic = BuckSchematicBuilder().build(
        design_input,
        selected_ic,
        design_result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )
    layout = BuckSchematicLayoutEngine().layout(schematic)
    request = ExportRequest.create(
        project_name="Buck_24V_to_5V_3A",
        output_root="output/altium_intermediate",
        schematic=schematic,
        layout=layout,
        metadata={
            "topology": "buck",
            "selected_component": {"part_number": selected_ic.part_number},
        },
    )
    result = export_design("altium", request)
    if not result.success:
        raise RuntimeError("; ".join(result.errors))
    print("Backend:", result.backend)
    print("Output:", result.output_directory)
    for artifact in result.artifacts:
        print(f"- {artifact.role}: {artifact.path}")
    for warning in result.warnings:
        print("Warning:", warning)


if __name__ == "__main__":
    main()
