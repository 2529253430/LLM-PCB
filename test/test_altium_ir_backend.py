from __future__ import annotations

import json
from pathlib import Path

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.design_ir import SchematicDesignAdapter
from src.export import ExportRequest, export_design
from src.export.altium import AltiumProjectBuilder
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def _design_layout_and_ir():
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
    project_ir = SchematicDesignAdapter().build(
        schematic,
        layout,
        project_name="Buck_IR",
        metadata={"topology": "buck"},
    )
    return schematic, layout, project_ir


def test_altium_builder_consumes_ir_directly() -> None:
    schematic, layout, project_ir = _design_layout_and_ir()

    model = AltiumProjectBuilder().build_from_ir(
        project_ir,
    )

    assert model.project_name == "Buck_IR"
    assert len(model.components) == len(schematic.components)
    assert len(model.nets) == len(schematic.nets)
    assert len(model.placements) == len(layout.symbols)
    assert len(model.wires) == len(layout.wires)
    assert model.metadata["source_ir_version"] == "1.0"
    assert model.metadata["target_eda"] == "altium"


def test_altium_backend_prefers_project_ir(
    tmp_path: Path,
) -> None:
    _, _, project_ir = _design_layout_and_ir()

    request = ExportRequest.create(
        project_name="Buck_IR",
        output_root=tmp_path,
        project_ir=project_ir,
        metadata={"requested_by": "phase14d"},
    )
    result = export_design("altium", request)

    assert result.success is True
    assert result.metadata["input_mode"] == (
        "universal_project_ir"
    )
    assert result.metadata["ir_validation"]["valid"] is True
    assert {artifact.role for artifact in result.artifacts} == {
        "altium_model",
        "manifest",
    }

    model_path = next(
        artifact.path
        for artifact in result.artifacts
        if artifact.role == "altium_model"
    )
    payload = json.loads(
        model_path.read_text(encoding="utf-8")
    )
    assert payload["metadata"]["requested_by"] == "phase14d"
    assert payload["metadata"]["source_ir_schema"] == (
        "llm-pcb.universal-project-ir"
    )


def test_altium_backend_legacy_path_uses_adapter(
    tmp_path: Path,
) -> None:
    schematic, layout, _ = _design_layout_and_ir()

    request = ExportRequest.create(
        project_name="Buck_Legacy",
        output_root=tmp_path,
        schematic=schematic,
        layout=layout,
    )
    result = export_design("altium", request)

    assert result.success is True
    assert result.metadata["input_mode"] == "legacy_adapter"
    assert result.metadata["ir_validation"]["valid"] is True


def test_altium_backend_reports_missing_ir_and_legacy_inputs(
    tmp_path: Path,
) -> None:
    request = ExportRequest.create(
        project_name="Buck",
        output_root=tmp_path,
    )

    result = export_design("altium", request)

    assert result.success is False
    assert "project_ir" in result.errors[0]
    assert "schematic" in result.errors[0]
    assert "layout" in result.errors[0]
