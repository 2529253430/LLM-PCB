from __future__ import annotations

from src.design.buck_engine import BuckDesignEngine, BuckDesignInput, BuckICParameters
from src.design_ir import SchematicDesignAdapter
from src.export.altium.schematic import AltiumSchDocWriter, AltiumSchematicBuilder
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def main() -> None:
    design_input = BuckDesignInput(18.0, 24.0, 5.0, 3.0)
    ic = BuckICParameters("EX36S4", 0.8, 500_000.0, 5.5)
    result = BuckDesignEngine().design(design_input, ic)
    schematic = BuckSchematicBuilder().build(
        design_input, ic, result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )
    layout = BuckSchematicLayoutEngine().layout(schematic)
    project_ir = SchematicDesignAdapter().build(
        schematic, layout, project_name="Buck_Phase16C"
    )
    document = AltiumSchematicBuilder().build_from_ir(project_ir)
    output = AltiumSchDocWriter().write(
        document,
        "output/altium_phase16c/Buck_Phase16C.SchDoc",
    )
    print(output)


if __name__ == "__main__":
    main()
