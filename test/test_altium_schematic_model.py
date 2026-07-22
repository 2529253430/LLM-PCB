from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.export.altium.schematic import (
    AltiumSchematicDocument,
    AltiumSchematicModelError,
    AltiumSchematicPreviewWriter,
    SchComponent,
    SchJunction,
    SchNetLabel,
    SchPin,
    SchPinElectricalType,
    SchPoint,
    SchSheet,
    SchWire,
)


def _document() -> AltiumSchematicDocument:
    return AltiumSchematicDocument(
        document_id="schematic:main",
        name="Main",
        sheet=SchSheet(name="Main"),
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
                        electrical_type=(
                            SchPinElectricalType.PASSIVE
                        ),
                    ),
                    SchPin(
                        pin_id="component:R1:pin:2",
                        name="2",
                        designator="2",
                        location=SchPoint(42.54, 30.0),
                        electrical_type=(
                            SchPinElectricalType.PASSIVE
                        ),
                        rotation_deg=180,
                    ),
                ),
            ),
        ),
        wires=(
            SchWire(
                wire_id="wire:1",
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
        junctions=(
            SchJunction(
                junction_id="junction:1",
                net_id="net:VIN",
                location=SchPoint(20.0, 30.0),
            ),
        ),
        metadata={"phase": "16A"},
    )


def test_document_validates_and_counts_objects() -> None:
    document = _document()

    document.validate()

    assert document.object_count == 4


def test_duplicate_component_reference_is_rejected() -> None:
    component = _document().components[0]
    document = AltiumSchematicDocument(
        document_id="schematic:main",
        name="Main",
        sheet=SchSheet(name="Main"),
        components=(
            component,
            SchComponent(
                component_id="component:R2",
                reference="R1",
                value="1k",
                symbol_name="Resistor",
                location=SchPoint(50.0, 30.0),
            ),
        ),
    )

    with pytest.raises(
        AltiumSchematicModelError,
        match="Duplicate schematic reference",
    ):
        document.validate()


def test_zero_length_wire_segment_is_rejected() -> None:
    wire = SchWire(
        wire_id="wire:bad",
        vertices=(
            SchPoint(10.0, 10.0),
            SchPoint(10.0, 10.0),
        ),
    )

    with pytest.raises(
        AltiumSchematicModelError,
        match="zero-length",
    ):
        wire.validate()


def test_invalid_rotation_is_rejected() -> None:
    component = SchComponent(
        component_id="component:R1",
        reference="R1",
        value="10k",
        symbol_name="Resistor",
        location=SchPoint(10.0, 10.0),
        rotation_deg=45,
    )

    with pytest.raises(
        AltiumSchematicModelError,
        match="rotation",
    ):
        component.validate()


def test_preview_writer_is_deterministic(
    tmp_path: Path,
) -> None:
    document = _document()
    output = tmp_path / "Main.sch-model.json"

    path = AltiumSchematicPreviewWriter().write(
        document,
        output,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["document_id"] == "schematic:main"
    assert payload["components"][0]["reference"] == "R1"
    assert payload["metadata"]["phase"] == "16A"
