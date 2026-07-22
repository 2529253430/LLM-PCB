from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.design_ir import (
    IRComponent,
    IRConstraintSet,
    IRNet,
    IRNetLabel,
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
    UniversalProjectValidator,
)


def _valid_project() -> UniversalProjectIR:
    components = (
        IRComponent(
            id="component:J1",
            reference="J1",
            value="INPUT",
            symbol_name="Connector_Generic:Conn_01x02",
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
    )
    nets = (
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
    )
    schematic = IRSchematic(
        name="Example",
        grid_mm=2.54,
        symbol_placements=(
            IRSymbolPlacement(
                component_id="component:J1",
                position=IRPoint(10.0, 20.0),
                body_size=IRSize(5.0, 7.5),
            ),
            IRSymbolPlacement(
                component_id="component:R1",
                position=IRPoint(30.0, 20.0),
                body_size=IRSize(5.0, 5.0),
            ),
        ),
        pin_placements=(
            IRPinPlacement(
                "component:J1",
                "1",
                IRPoint(15.0, 18.0),
            ),
            IRPinPlacement(
                "component:J1",
                "2",
                IRPoint(15.0, 22.0),
            ),
            IRPinPlacement(
                "component:R1",
                "1",
                IRPoint(30.0, 15.0),
            ),
            IRPinPlacement(
                "component:R1",
                "2",
                IRPoint(30.0, 25.0),
            ),
        ),
        wires=(
            IRWire(
                "net:VIN",
                IRSegment(
                    IRPoint(15.0, 18.0),
                    IRPoint(30.0, 18.0),
                ),
            ),
            IRWire(
                "net:GND",
                IRSegment(
                    IRPoint(15.0, 22.0),
                    IRPoint(30.0, 22.0),
                ),
            ),
        ),
        labels=(
            IRNetLabel(
                "net:VIN",
                IRPoint(15.0, 18.0),
                "VIN",
            ),
            IRNetLabel(
                "net:GND",
                IRPoint(15.0, 22.0),
                "GND",
            ),
        ),
    )
    return UniversalProjectIR(
        project_id="project:example",
        project_name="Example",
        schematic=schematic,
        components=components,
        nets=nets,
        constraints=IRConstraintSet(
            minimum_track_width_mm=0.20,
            preferred_track_width_mm=0.25,
            minimum_clearance_mm=0.20,
            via_diameter_mm=0.80,
            via_drill_mm=0.40,
        ),
        metadata={"topology": "example"},
    )


def test_valid_project_passes_validation() -> None:
    report = UniversalProjectValidator().validate(
        _valid_project()
    )

    assert report.valid is True
    assert report.errors == []


def test_pin_cannot_belong_to_multiple_nets() -> None:
    project = _valid_project()
    project.nets = project.nets + (
        IRNet(
            id="net:OTHER",
            name="OTHER",
            connections=(
                IRPinRef("component:J1", "1"),
                IRPinRef("component:R1", "2"),
            ),
        ),
    )

    report = UniversalProjectValidator().validate(project)

    assert report.valid is False
    assert any(
        issue.code == "PIN_MULTIPLE_NETS"
        for issue in report.errors
    )


def test_missing_symbol_placement_is_reported() -> None:
    project = _valid_project()
    project.schematic = IRSchematic(
        name=project.schematic.name,
        grid_mm=project.schematic.grid_mm,
        symbol_placements=(
            project.schematic.symbol_placements[0],
        ),
        pin_placements=project.schematic.pin_placements,
        wires=project.schematic.wires,
        labels=project.schematic.labels,
    )

    report = UniversalProjectValidator().validate(project)

    assert report.valid is False
    assert any(
        issue.code == "SYMBOL_PLACEMENT_MISSING"
        for issue in report.errors
    )


def test_serializer_is_deterministic(
    tmp_path: Path,
) -> None:
    project = _valid_project()
    serializer = UniversalProjectIRSerializer()

    first = serializer.write(
        project,
        tmp_path / "first",
    )
    second = serializer.write(
        project,
        tmp_path / "second",
    )

    assert (
        first["project_ir"].read_bytes()
        == second["project_ir"].read_bytes()
    )
    assert (
        first["validation"].read_bytes()
        == second["validation"].read_bytes()
    )

    payload = json.loads(
        first["project_ir"].read_text(encoding="utf-8")
    )
    assert payload["schema"] == (
        "llm-pcb.universal-project-ir"
    )
    assert payload["schema_version"] == "1.0"


def test_serializer_rejects_invalid_project(
    tmp_path: Path,
) -> None:
    project = _valid_project()
    project.project_name = ""

    with pytest.raises(ValueError):
        UniversalProjectIRSerializer().write(
            project,
            tmp_path / "invalid",
        )
