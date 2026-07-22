from __future__ import annotations

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.design_ir import SchematicDesignAdapter
from src.export.altium.schematic import (
    AltiumSchematicBuilder,
    AltiumSchematicPreviewWriter,
)
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def main() -> None:
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
    )
    ic = BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        switch_current_limit_a=5.5,
    )

    result = BuckDesignEngine().design(
        design_input,
        ic,
    )
    schematic = BuckSchematicBuilder().build(
        design_input,
        ic,
        result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )
    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    project_ir = SchematicDesignAdapter().build(
        schematic,
        layout,
        project_name="Buck_Phase16B",
        metadata={
            "topology": "buck",
            "example": "phase16b",
        },
    )
    document = (
        AltiumSchematicBuilder().build_from_ir(
            project_ir
        )
    )

    output = AltiumSchematicPreviewWriter().write(
        document,
        (
            "output/altium_phase16b/"
            "Buck_Phase16B.sch-model.json"
        ),
    )
    print(output)


if __name__ == "__main__":
    main()
