from __future__ import annotations

from src.design_ir import (
    SchematicDesignAdapter,
    UniversalProjectIRSerializer,
)
from src.schematic.layout import (
    PinLayout,
    Point,
    SchematicLayout,
    SymbolLayout,
    WireSegment,
)
from src.schematic.model import (
    PinReference,
    SchematicComponent,
    SchematicDesign,
    SchematicNet,
    SchematicPin,
)


def main() -> None:
    design = SchematicDesign(name="Altium_IR_Adapter")
    design.add_component(
        SchematicComponent(
            reference="J1",
            value="INPUT",
            symbol_name="Connector_Generic:Conn_01x02",
            footprint_name="Connector:Input",
            pins=(
                SchematicPin("1", "VIN", "power_in"),
                SchematicPin("2", "GND", "power_in"),
            ),
        )
    )
    design.add_component(
        SchematicComponent(
            reference="R1",
            value="10k",
            symbol_name="Device:R",
            footprint_name="Resistor_SMD:R_0603",
            pins=(
                SchematicPin("1", "1"),
                SchematicPin("2", "2"),
            ),
        )
    )
    design.add_net(
        SchematicNet(
            name="VIN",
            connections=(
                PinReference("J1", "1"),
                PinReference("R1", "1"),
            ),
        )
    )
    design.add_net(
        SchematicNet(
            name="GND",
            connections=(
                PinReference("J1", "2"),
                PinReference("R1", "2"),
            ),
        )
    )

    layout = SchematicLayout(
        design_name=design.name,
        grid_mm=2.54,
    )
    layout.add_symbol(
        SymbolLayout("J1", Point(20.0, 30.0))
    )
    layout.add_symbol(
        SymbolLayout("R1", Point(50.0, 30.0))
    )
    layout.add_pin(
        PinLayout("J1", "1", Point(25.0, 28.0))
    )
    layout.add_pin(
        PinLayout("J1", "2", Point(25.0, 32.0))
    )
    layout.add_pin(
        PinLayout("R1", "1", Point(50.0, 28.0))
    )
    layout.add_pin(
        PinLayout("R1", "2", Point(50.0, 32.0))
    )
    layout.add_wire(
        WireSegment(
            "VIN",
            Point(25.0, 28.0),
            Point(50.0, 28.0),
        )
    )
    layout.add_wire(
        WireSegment(
            "GND",
            Point(25.0, 32.0),
            Point(50.0, 32.0),
        )
    )

    project_ir = SchematicDesignAdapter().build(
        design,
        layout,
        metadata={"export_target": "Altium Designer"},
    )

    paths = UniversalProjectIRSerializer().write(
        project_ir,
        "output/altium_ir/Altium_IR_Adapter",
    )

    print("Altium-targeted Universal IR generated:")
    for role, path in paths.items():
        print(f"- {role}: {path}")


if __name__ == "__main__":
    main()
