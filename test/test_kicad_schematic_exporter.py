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
)
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import (
    BuckSchematicLayoutEngine,
    Point,
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

    design = BuckSchematicBuilder().build(
        design_input,
        ic,
        result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )

    layout = BuckSchematicLayoutEngine().layout(design)

    return design, layout


def test_export_creates_modern_kicad_schematic(
    tmp_path: Path,
) -> None:
    design, layout = _design_and_layout()
    output = tmp_path / "buck.kicad_sch"

    result = KiCadSchematicExporter().export(
        design,
        layout,
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


def test_export_uses_layout_symbol_positions(
    tmp_path: Path,
) -> None:
    design, _ = _design_and_layout()

    layout = BuckSchematicLayoutEngine().layout(
        design,
        symbol_positions={
            "U1": Point(101.6, 81.28),
        },
    )

    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        design,
        layout,
        output,
    )

    text = output.read_text(encoding="utf-8")

    assert "(at 101.600 81.280 0)" in text


def test_export_contains_all_layout_wires(
    tmp_path: Path,
) -> None:
    design, layout = _design_and_layout()
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        design,
        layout,
        output,
    )

    text = output.read_text(encoding="utf-8")

    assert text.count("(wire") == len(layout.wires)

    for wire in layout.wires:
        assert (
            f"(xy {wire.start.x:.3f} "
            f"{wire.start.y:.3f})"
        ) in text
        assert (
            f"(xy {wire.end.x:.3f} "
            f"{wire.end.y:.3f})"
        ) in text


def test_export_contains_all_layout_junctions(
    tmp_path: Path,
) -> None:
    design, layout = _design_and_layout()
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        design,
        layout,
        output,
    )

    text = output.read_text(encoding="utf-8")

    assert text.count("(junction") == len(
        layout.junctions
    )


def test_export_contains_all_layout_labels(
    tmp_path: Path,
) -> None:
    design, layout = _design_and_layout()
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        design,
        layout,
        output,
    )

    text = output.read_text(encoding="utf-8")

    assert text.count("(label ") == len(layout.labels)

    for label in layout.labels:
        assert f'(label "{label.net_name}"' in text


def test_embeds_all_component_symbols(
    tmp_path: Path,
) -> None:
    design, layout = _design_and_layout()
    output = tmp_path / "buck.kicad_sch"

    KiCadSchematicExporter().export(
        design,
        layout,
        output,
    )

    text = output.read_text(encoding="utf-8")

    for component in design.components:
        assert (
            f"LLMPCB_{component.reference}_SYMBOL"
            in text
        )
        assert (
            f'(reference "{component.reference}")'
            in text
        )


def test_wrong_extension_is_rejected(
    tmp_path: Path,
) -> None:
    design, layout = _design_and_layout()

    with pytest.raises(
        KiCadSchematicExportError,
        match=".kicad_sch extension",
    ):
        KiCadSchematicExporter().export(
            design,
            layout,
            tmp_path / "buck.sch",
        )
