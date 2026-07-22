from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.export.kicad_project_exporter import (
    KiCadProjectExportError,
    KiCadProjectExporter,
    KiCadProjectMetadata,
    KiCadProjectValidator,
)
from src.schematic.buck_builder import (
    BuckSchematicBuilder,
)
from src.schematic.layout import (
    BuckSchematicLayoutEngine,
)


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

    return schematic, layout


def _write_test_pcb(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "(kicad_pcb",
                "  (version 20240108)",
                "  (generator pcbnew)",
                "  (general",
                "    (thickness 1.6)",
                "  )",
                "  (footprint \"Test:Part\"",
                "    (layer \"F.Cu\")",
                "    (at 10 10)",
                "  )",
                "  (segment",
                "    (start 10 10)",
                "    (end 20 10)",
                "    (width 0.25)",
                "    (layer \"F.Cu\")",
                "    (net 1)",
                "  )",
                ")",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_exports_complete_project(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)

    project = KiCadProjectExporter().export(
        project_name="Buck_24V_to_5V_3A",
        schematic=schematic,
        layout=layout,
        pcb_source_path=pcb_source,
        output_root=tmp_path / "output",
    )

    assert project.project_file.exists()
    assert project.schematic_file.exists()
    assert project.pcb_file.exists()
    assert project.metadata_file.exists()
    assert project.validation_file.exists()


def test_project_files_share_same_stem(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)

    project = KiCadProjectExporter().export(
        project_name="Buck Design",
        schematic=schematic,
        layout=layout,
        pcb_source_path=pcb_source,
        output_root=tmp_path,
    )

    assert project.name == "Buck_Design"
    assert project.project_file.stem == "Buck_Design"
    assert project.schematic_file.stem == "Buck_Design"
    assert project.pcb_file.stem == "Buck_Design"


def test_kicad_pro_is_valid_json(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)

    project = KiCadProjectExporter().export(
        "Buck",
        schematic,
        layout,
        pcb_source,
        tmp_path,
    )

    payload = json.loads(
        project.project_file.read_text(
            encoding="utf-8"
        )
    )

    assert payload["meta"]["filename"] == (
        "Buck.kicad_pro"
    )
    assert payload["meta"]["version"] == 1
    assert "schematic" in payload
    assert "pcbnew" in payload


def test_metadata_contains_design_counts(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)

    metadata = KiCadProjectMetadata(
        topology="buck",
        requirements={
            "vin_max_v": 24.0,
            "vout_v": 5.0,
            "iout_a": 3.0,
        },
        selected_component={
            "part_number": "EX36S4",
        },
    )

    project = KiCadProjectExporter().export(
        "Buck",
        schematic,
        layout,
        pcb_source,
        tmp_path,
        metadata=metadata,
    )

    payload = json.loads(
        project.metadata_file.read_text(
            encoding="utf-8"
        )
    )

    assert payload["design"]["topology"] == "buck"
    assert payload["design"]["component_count"] == (
        len(schematic.components)
    )
    assert payload["design"]["net_count"] == (
        len(schematic.nets)
    )
    assert (
        payload["selected_component"]["part_number"]
        == "EX36S4"
    )


def test_validation_report_is_valid(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)

    project = KiCadProjectExporter().export(
        "Buck",
        schematic,
        layout,
        pcb_source,
        tmp_path,
    )

    payload = json.loads(
        project.validation_file.read_text(
            encoding="utf-8"
        )
    )

    assert payload["valid"] is True
    assert payload["errors"] == []


def test_missing_pcb_is_rejected(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()

    with pytest.raises(
        KiCadProjectExportError,
        match="does not exist",
    ):
        KiCadProjectExporter().export(
            "Buck",
            schematic,
            layout,
            tmp_path / "missing.kicad_pcb",
            tmp_path,
        )


def test_wrong_pcb_extension_is_rejected(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    source = tmp_path / "board.txt"
    source.write_text(
        "(kicad_pcb)",
        encoding="utf-8",
    )

    with pytest.raises(
        KiCadProjectExportError,
        match=".kicad_pcb extension",
    ):
        KiCadProjectExporter().export(
            "Buck",
            schematic,
            layout,
            source,
            tmp_path,
        )


def test_existing_directory_can_be_protected(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)

    directory = tmp_path / "Buck"
    directory.mkdir()

    with pytest.raises(
        KiCadProjectExportError,
        match="already exists",
    ):
        KiCadProjectExporter().export(
            "Buck",
            schematic,
            layout,
            pcb_source,
            tmp_path,
            overwrite=False,
        )


def test_validator_detects_missing_file(
    tmp_path: Path,
) -> None:
    schematic, layout = _design_and_layout()
    pcb_source = tmp_path / "source.kicad_pcb"
    _write_test_pcb(pcb_source)

    project = KiCadProjectExporter().export(
        "Buck",
        schematic,
        layout,
        pcb_source,
        tmp_path,
    )

    project.pcb_file.unlink()

    result = KiCadProjectValidator().validate(
        project,
        schematic,
        layout,
    )

    assert result["valid"] is False
    assert any(
        "Missing pcb file" in error
        for error in result["errors"]
    )
