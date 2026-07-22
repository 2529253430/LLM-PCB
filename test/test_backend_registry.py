from __future__ import annotations

from pathlib import Path

import pytest

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.export import (
    AltiumBackend,
    BackendRegistry,
    BackendRegistryError,
    ExportRequest,
    KiCadBackend,
    export_design,
)
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


def _write_test_pcb(path: Path) -> None:
    path.write_text(
        "(kicad_pcb\n"
        " (version 20240108)\n"
        " (generator pcbnew)\n"
        " (general (thickness 1.6))\n"
        ")\n",
        encoding="utf-8",
    )


def test_default_backends_are_registered() -> None:
    registry = BackendRegistry((KiCadBackend(), AltiumBackend()))
    assert registry.available_backends() == ("altium", "kicad")


def test_duplicate_backend_is_rejected() -> None:
    registry = BackendRegistry((KiCadBackend(),))
    with pytest.raises(BackendRegistryError, match="already registered"):
        registry.register(KiCadBackend())


def test_unknown_backend_has_available_names() -> None:
    registry = BackendRegistry((KiCadBackend(),))
    with pytest.raises(BackendRegistryError, match="Available backends"):
        registry.get("missing")


def test_kicad_backend_exports_complete_project(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)
    request = ExportRequest.create(
        project_name="Backend Buck",
        output_root=tmp_path / "projects",
        schematic=schematic,
        layout=layout,
        pcb_source_path=pcb_source,
        metadata={"topology": "buck"},
    )
    result = export_design("kicad", request)
    assert result.success is True
    assert result.output_directory is not None
    assert len(result.artifacts) == 5
    assert all(path.exists() for path in result.files)
    assert {artifact.role for artifact in result.artifacts} == {
        "project",
        "schematic",
        "pcb",
        "metadata",
        "validation",
    }


def test_kicad_backend_reports_missing_inputs(
    tmp_path: Path,
) -> None:
    request = ExportRequest.create("Buck", tmp_path)
    result = export_design("kicad", request)
    assert result.success is False
    assert "schematic" in result.errors[0]
    assert "layout" in result.errors[0]
    assert "pcb_source_path" in result.errors[0]


def test_altium_backend_reports_missing_inputs(
    tmp_path: Path,
) -> None:
    request = ExportRequest.create("Buck", tmp_path)
    result = export_design("altium", request)
    assert result.success is False
    assert result.artifacts == []
    assert "schematic" in result.errors[0]
    assert "layout" in result.errors[0]
    assert result.metadata["capabilities"]["native_format"] is False
