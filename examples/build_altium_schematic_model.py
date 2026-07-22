from __future__ import annotations

from src.export.altium.schematic import (
    AltiumSchematicDocument,
    AltiumSchematicPreviewWriter,
    SchComponent,
    SchNetLabel,
    SchPin,
    SchPinElectricalType,
    SchPoint,
    SchSheet,
    SchWire,
)


def main() -> None:
    document = AltiumSchematicDocument(
        document_id="schematic:main",
        name="Example",
        sheet=SchSheet(
            name="Example",
            title="Phase 16A Object Model",
        ),
        components=(
            SchComponent(
                component_id="component:R1",
                reference="R1",
                value="10k",
                symbol_name="Resistor",
                location=SchPoint(40.0, 30.0),
                pins=(
                    SchPin(
                        pin_id="component:R1:pin:1",
                        name="1",
                        designator="1",
                        location=SchPoint(37.46, 30.0),
                        electrical_type=SchPinElectricalType.PASSIVE,
                    ),
                    SchPin(
                        pin_id="component:R1:pin:2",
                        name="2",
                        designator="2",
                        location=SchPoint(42.54, 30.0),
                        electrical_type=SchPinElectricalType.PASSIVE,
                        rotation_deg=180,
                    ),
                ),
            ),
        ),
        wires=(
            SchWire(
                wire_id="wire:VIN",
                net_id="net:VIN",
                vertices=(
                    SchPoint(20.0, 30.0),
                    SchPoint(37.46, 30.0),
                ),
            ),
        ),
        labels=(
            SchNetLabel(
                label_id="label:VIN",
                text="VIN",
                net_id="net:VIN",
                location=SchPoint(20.0, 30.0),
            ),
        ),
        metadata={"phase": "16A"},
    )

    path = AltiumSchematicPreviewWriter().write(
        document,
        "output/altium_phase16a/Example.sch-model.json",
    )
    print(path)


if __name__ == "__main__":
    main()
