from __future__ import annotations

from src.design_ir import (
    IRComponent,
    IRConstraintSet,
    IRNet,
    IRPin,
    IRPinPlacement,
    IRPinRef,
    IRPoint,
    IRSchematic,
    IRSegment,
    IRSize,
    IRSymbolPlacement,
    IRWire,
    UniversalProjectIR,
    UniversalProjectIRSerializer,
)


def main() -> None:
    project = UniversalProjectIR(
        project_id="project:phase14b-example",
        project_name="Phase14B_Example",
        components=(
            IRComponent(
                id="component:J1",
                reference="J1",
                value="INPUT",
                symbol_name=(
                    "Connector_Generic:Conn_01x02"
                ),
                pins=(
                    IRPin("1", "VIN", "power_in"),
                    IRPin("2", "GND", "power_in"),
                ),
            ),
            IRComponent(
                id="component:R1",
                reference="R1",
                value="10k",
                symbol_name="Device:R",
                pins=(
                    IRPin("1", "1"),
                    IRPin("2", "2"),
                ),
            ),
        ),
        nets=(
            IRNet(
                id="net:VIN",
                name="VIN",
                connections=(
                    IRPinRef("component:J1", "1"),
                    IRPinRef("component:R1", "1"),
                ),
            ),
            IRNet(
                id="net:GND",
                name="GND",
                connections=(
                    IRPinRef("component:J1", "2"),
                    IRPinRef("component:R1", "2"),
                ),
            ),
        ),
        schematic=IRSchematic(
            name="Phase14B_Example",
            grid_mm=2.54,
            symbol_placements=(
                IRSymbolPlacement(
                    "component:J1",
                    IRPoint(20.0, 30.0),
                    IRSize(7.5, 7.5),
                ),
                IRSymbolPlacement(
                    "component:R1",
                    IRPoint(50.0, 30.0),
                    IRSize(5.0, 5.0),
                ),
            ),
            pin_placements=(
                IRPinPlacement(
                    "component:J1",
                    "1",
                    IRPoint(25.0, 28.0),
                ),
                IRPinPlacement(
                    "component:J1",
                    "2",
                    IRPoint(25.0, 32.0),
                ),
                IRPinPlacement(
                    "component:R1",
                    "1",
                    IRPoint(50.0, 25.0),
                ),
                IRPinPlacement(
                    "component:R1",
                    "2",
                    IRPoint(50.0, 35.0),
                ),
            ),
            wires=(
                IRWire(
                    "net:VIN",
                    IRSegment(
                        IRPoint(25.0, 28.0),
                        IRPoint(50.0, 28.0),
                    ),
                ),
                IRWire(
                    "net:GND",
                    IRSegment(
                        IRPoint(25.0, 32.0),
                        IRPoint(50.0, 32.0),
                    ),
                ),
            ),
        ),
        constraints=IRConstraintSet(
            minimum_track_width_mm=0.20,
            preferred_track_width_mm=0.25,
            minimum_clearance_mm=0.20,
        ),
        metadata={"phase": "14B"},
    )

    paths = UniversalProjectIRSerializer().write(
        project,
        "output/universal_ir/Phase14B_Example",
    )
    print("Universal IR exported:")
    for role, path in paths.items():
        print(f"- {role}: {path}")


if __name__ == "__main__":
    main()
