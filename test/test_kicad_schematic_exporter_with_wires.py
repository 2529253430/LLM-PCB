from __future__ import annotations

from pathlib import Path

import pytest

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.export.kicad_schematic_exporter import (
    KiCadSchematicExportError,
    KiCadSchematicExporter,
    SymbolPlacement,
)
from src.schematic.buck_builder import BuckSchematicBuilder


def _schematic():
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

    return BuckSchematicBuilder().build(
        design_input,
        ic,
        result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )


def test_export_creates_modern_kicad_schematic(
    tmp_path: Path,
) -> None:
    output = tmp_path / "buck.kicad_sch"

    result = KiCadSchematicExporter().export(
        _schematic(),
        output,
    )

    assert result == output
    assert output.exists()

    text = output.read_text(encoding="utf-8")

    assert text.startswith("(kicad_sch")
    assert "(version 20231120)" in text
    assert "(generator llm_pcb)" in text
    assert "(lib_symbols" in text
    assert "(sheet_instances" in text


def test_embeds_all_component_symbols(
    tmp_path: Path,
) -> None:
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        _schematic(),
        output,
    )

    text = output.read_text(encoding="utf-8")

    for reference in (
        "J1",
        "J2",
        "U1",
        "CIN",
        "L1",
        "COUT",
        "R1",
        "R2",
        "CBOOT",
    ):
        assert f'LLMPCB_{reference}_SYMBOL' in text
        assert f'(reference "{reference}")' in text

    assert "LLMPCB:" not in text


def test_exports_all_net_labels(
    tmp_path: Path,
) -> None:
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        _schematic(),
        output,
    )

    text = output.read_text(encoding="utf-8")

    for net_name in (
        "VIN",
        "SW",
        "VOUT",
        "FB",
        "GND",
        "BOOT",
    ):
        assert f'(label "{net_name}"' in text


def test_each_symbol_pin_has_instance_uuid(
    tmp_path: Path,
) -> None:
    schematic = _schematic()
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        schematic,
        output,
    )

    text = output.read_text(encoding="utf-8")

    expected_pin_count = sum(
        len(component.pins)
        for component in schematic.components
    )

    assert text.count('(pin "') >= expected_pin_count


def test_wrong_extension_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        KiCadSchematicExportError,
        match=".kicad_sch extension",
    ):
        KiCadSchematicExporter().export(
            _schematic(),
            tmp_path / "buck.sch",
        )


def test_missing_placement_is_rejected(
    tmp_path: Path,
) -> None:
    exporter = KiCadSchematicExporter()
    exporter.DEFAULT_PLACEMENTS = {
        key: value
        for key, value in exporter.DEFAULT_PLACEMENTS.items()
        if key != "U1"
    }

    with pytest.raises(
        KiCadSchematicExportError,
        match="U1",
    ):
        exporter.export(
            _schematic(),
            tmp_path / "buck.kicad_sch",
        )


def test_nonzero_rotation_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        KiCadSchematicExportError,
        match="zero-degree",
    ):
        KiCadSchematicExporter().export(
            _schematic(),
            tmp_path / "buck.kicad_sch",
            placements={
                "U1": SymbolPlacement(
                    90.0,
                    75.0,
                    rotation_deg=90,
                )
            },
        )


def test_export_contains_visible_wires(
    tmp_path: Path,
) -> None:
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        _schematic(),
        output,
    )

    text = output.read_text(encoding="utf-8")

    assert "(wire" in text
    assert text.count("(wire") >= 10
    assert "(pts" in text
    assert "(xy " in text


def test_export_contains_branch_junctions(
    tmp_path: Path,
) -> None:
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        _schematic(),
        output,
    )

    text = output.read_text(encoding="utf-8")

    assert "(junction" in text
    assert text.count("(junction") >= 6
