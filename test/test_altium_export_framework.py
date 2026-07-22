from __future__ import annotations

import json
from pathlib import Path

from src.design.buck_engine import BuckDesignEngine, BuckDesignInput, BuckICParameters
from src.export import ExportRequest, export_design
from src.export.altium import AltiumIntermediateWriter, AltiumProjectBuilder
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def _design_and_layout():
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
    result = BuckDesignEngine().design(design_input, ic)
    schematic = BuckSchematicBuilder().build(
        design_input,
        ic,
        result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )
    layout = BuckSchematicLayoutEngine().layout(schematic)
    return schematic, layout


def test_builder_maps_complete_schematic() -> None:
    schematic, layout = _design_and_layout()
    model = AltiumProjectBuilder().build(
        project_name="Buck",
        schematic=schematic,
        layout=layout,
        metadata={"topology": "buck"},
    )
    assert model.project_name == "Buck"
    assert len(model.components) == len(schematic.components)
    assert len(model.nets) == len(schematic.nets)
    assert len(model.placements) == len(schematic.components)
    assert len(model.wires) == len(layout.wires)
    assert model.metadata["topology"] == "buck"


def test_writer_creates_reviewable_package(tmp_path: Path) -> None:
    schematic, layout = _design_and_layout()
    model = AltiumProjectBuilder().build(
        project_name="Buck",
        schematic=schematic,
        layout=layout,
    )
    paths = AltiumIntermediateWriter().write(model, tmp_path / "Buck")
    assert set(paths) == {"altium_model", "manifest"}
    assert all(path.exists() for path in paths.values())
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["native_altium"] is False
    assert manifest["project_name"] == "Buck"


def test_altium_backend_exports_intermediate_package(tmp_path: Path) -> None:
    schematic, layout = _design_and_layout()
    request = ExportRequest.create(
        project_name="Buck",
        output_root=tmp_path,
        schematic=schematic,
        layout=layout,
        metadata={"topology": "buck"},
    )
    result = export_design("altium", request)
    assert result.success is True
    assert result.output_directory == tmp_path / "Buck"
    assert {artifact.role for artifact in result.artifacts} == {"altium_model", "manifest"}
    assert all(path.exists() for path in result.files)
    assert result.metadata["format"] == "llm-pcb-altium-intermediate"
    assert result.metadata["capabilities"]["native_format"] is False


def test_altium_backend_reports_missing_inputs(tmp_path: Path) -> None:
    request = ExportRequest.create(project_name="Buck", output_root=tmp_path)
    result = export_design("altium", request)
    assert result.success is False
    assert "schematic" in result.errors[0]
    assert "layout" in result.errors[0]
