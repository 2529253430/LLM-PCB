from __future__ import annotations

import json
from pathlib import Path

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.design_ir import SchematicDesignAdapter
from src.export.altium.schematic import (
    AltiumSchematicBuilder,
    AltiumSchematicDocument,
    AltiumSchematicPreviewWriter,
    SchPinElectricalType,
)
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def _project_ir():
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
        metadata={"topology": "buck"},
    )
    return project_ir


def test_builder_returns_altium_schematic_document() -> None:
    project_ir = _project_ir()

    document = AltiumSchematicBuilder().build_from_ir(
        project_ir
    )

    assert isinstance(
        document,
        AltiumSchematicDocument,
    )
    assert document.name == project_ir.schematic.name
    assert document.sheet.grid_mm == (
        project_ir.schematic.grid_mm
    )
    document.validate()


def test_builder_maps_all_components_and_wires() -> None:
    project_ir = _project_ir()

    document = AltiumSchematicBuilder().build_from_ir(
        project_ir
    )

    assert len(document.components) == len(
        project_ir.components
    )
    assert len(document.wires) == len(
        project_ir.schematic.wires
    )
    assert len(document.junctions) == len(
        project_ir.schematic.junctions
    )


def test_builder_maps_component_identity_and_pins() -> None:
    project_ir = _project_ir()

    document = AltiumSchematicBuilder().build_from_ir(
        project_ir
    )

    source = next(
        component
        for component in project_ir.components
        if component.reference == "U1"
    )
    mapped = next(
        component
        for component in document.components
        if component.reference == "U1"
    )

    assert mapped.component_id == source.id
    assert mapped.value == source.value
    assert mapped.symbol_name == source.symbol_name
    assert mapped.footprint == source.footprint_name
    assert len(mapped.pins) == len(source.pins)
    assert all(
        pin.electrical_type
        is not SchPinElectricalType.UNSPECIFIED
        for pin in mapped.pins
    )


def test_builder_preserves_all_net_names() -> None:
    project_ir = _project_ir()

    document = AltiumSchematicBuilder().build_from_ir(
        project_ir
    )

    assert {
        label.text
        for label in document.labels
    } >= {
        net.name
        for net in project_ir.nets
    }
    assert {
        "VIN",
        "SW",
        "VOUT",
        "FB",
        "GND",
        "BOOT",
    } <= {
        label.text
        for label in document.labels
    }


def test_builder_adds_mapping_metadata() -> None:
    project_ir = _project_ir()

    document = AltiumSchematicBuilder().build_from_ir(
        project_ir
    )

    assert (
        document.metadata["source_ir_version"]
        == project_ir.schema_version
    )
    assert (
        document.metadata["source_project_id"]
        == project_ir.project_id
    )
    assert document.metadata["target_eda"] == "altium"
    assert (
        document.metadata["mapping_stage"]
        == "phase16b"
    )
    assert document.metadata["topology"] == "buck"


def test_preview_writer_accepts_builder_output(
    tmp_path: Path,
) -> None:
    project_ir = _project_ir()
    document = AltiumSchematicBuilder().build_from_ir(
        project_ir
    )

    output = (
        tmp_path
        / "Buck_Phase16B.sch-model.json"
    )
    result = AltiumSchematicPreviewWriter().write(
        document,
        output,
    )

    payload = json.loads(
        result.read_text(encoding="utf-8")
    )
    assert payload["name"] == document.name
    assert len(payload["components"]) == len(
        project_ir.components
    )
    assert {
        label["text"]
        for label in payload["labels"]
    } >= {
        net.name
        for net in project_ir.nets
    }
