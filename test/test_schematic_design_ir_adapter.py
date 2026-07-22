from __future__ import annotations

from pathlib import Path

from src.design_ir import (
    SchematicDesignAdapter,
    UniversalProjectIRSerializer,
    UniversalProjectValidator,
)
from src.schematic.layout import (
    NetLabelLayout,
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


def _source_design() -> tuple[SchematicDesign, SchematicLayout]:
    design = SchematicDesign(
        name="Adapter_Example",
        metadata={"topology": "buck"},
    )
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
            fields={"Voltage": "24V"},
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
        design_name="Adapter_Example",
        grid_mm=2.54,
    )
    layout.add_symbol(
        SymbolLayout(
            reference="J1",
            position=Point(20.0, 30.0),
            body_width_mm=7.5,
            body_height_mm=7.5,
        )
    )
    layout.add_symbol(
        SymbolLayout(
            reference="R1",
            position=Point(50.0, 30.0),
            body_width_mm=5.0,
            body_height_mm=5.0,
        )
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
    layout.add_label(
        NetLabelLayout("VIN", Point(25.0, 28.0))
    )
    layout.add_label(
        NetLabelLayout("GND", Point(25.0, 32.0))
    )

    return design, layout


def test_adapter_preserves_design_counts() -> None:
    design, layout = _source_design()

    project = SchematicDesignAdapter().build(
        design,
        layout,
    )

    assert len(project.components) == len(design.components)
    assert len(project.nets) == len(design.nets)
    assert len(project.schematic.symbol_placements) == (
        len(layout.symbols)
    )
    assert len(project.schematic.pin_placements) == (
        len(layout.pins)
    )
    assert len(project.schematic.wires) == len(layout.wires)


def test_adapter_preserves_component_fields() -> None:
    design, layout = _source_design()

    project = SchematicDesignAdapter().build(
        design,
        layout,
    )
    j1 = next(
        component
        for component in project.components
        if component.reference == "J1"
    )

    assert j1.footprint_name == "Connector:Input"
    assert j1.parameters["Voltage"] == "24V"
    assert j1.id == "component:J1"


def test_adapter_generates_valid_ir() -> None:
    design, layout = _source_design()

    project = SchematicDesignAdapter().build(
        design,
        layout,
    )
    report = UniversalProjectValidator().validate(project)

    assert report.valid is True
    assert project.metadata["target_eda"] == "altium"


def test_adapter_output_is_deterministic(
    tmp_path: Path,
) -> None:
    design, layout = _source_design()
    adapter = SchematicDesignAdapter()
    serializer = UniversalProjectIRSerializer()

    first_project = adapter.build(design, layout)
    second_project = adapter.build(design, layout)

    first_paths = serializer.write(
        first_project,
        tmp_path / "first",
    )
    second_paths = serializer.write(
        second_project,
        tmp_path / "second",
    )

    assert (
        first_paths["project_ir"].read_bytes()
        == second_paths["project_ir"].read_bytes()
    )
