from __future__ import annotations

from pathlib import Path

from src.export.altium.schematic import (
    AltiumSchDocInspector,
    AltiumSchDocWriter,
    AltiumSchematicDocument,
    SchComponent,
    SchJunction,
    SchNetLabel,
    SchPin,
    SchPoint,
    SchSheet,
    SchWire,
)


def _document() -> AltiumSchematicDocument:
    return AltiumSchematicDocument(
        document_id="phase16c:minimal",
        name="Minimal",
        sheet=SchSheet(name="Minimal", title="Phase 16C"),
        components=(
            SchComponent(
                component_id="component:r1",
                reference="R1",
                value="10K",
                symbol_name="Resistor",
                location=SchPoint(127.0, 142.24),
                pins=(
                    SchPin("r1:1", "1", "1", SchPoint(129.54, 142.24), rotation_deg=180),
                    SchPin("r1:2", "2", "2", SchPoint(134.62, 142.24)),
                ),
            ),
        ),
        wires=(
            SchWire("wire:test", (SchPoint(134.62, 142.24), SchPoint(165.1, 142.24))),
        ),
        labels=(
            SchNetLabel("label:test", "TEST_NET", SchPoint(165.1, 142.24)),
        ),
        junctions=(
            SchJunction("junction:test", SchPoint(147.32, 142.24)),
        ),
    )


def test_writer_creates_native_cfb_schdoc(tmp_path: Path) -> None:
    output = AltiumSchDocWriter().write(_document(), tmp_path / "Minimal.SchDoc")
    assert output.read_bytes()[:8] == bytes.fromhex("D0CF11E0A1B11AE1")
    streams = AltiumSchDocInspector().streams(output)
    assert set(streams) == {"Additional", "FileHeader", "Storage"}


def test_writer_emits_core_native_records(tmp_path: Path) -> None:
    output = AltiumSchDocWriter().write(_document(), tmp_path / "Minimal.SchDoc")
    records = AltiumSchDocInspector().records(output)
    types = [record.record_type for record in records]
    assert types[0] is None
    assert 31 in types
    assert 1 in types
    assert types.count(2) == 2
    assert 27 in types
    assert 25 in types
    assert 29 in types


def test_output_is_deterministic(tmp_path: Path) -> None:
    first = AltiumSchDocWriter().write(_document(), tmp_path / "a.SchDoc").read_bytes()
    second = AltiumSchDocWriter().write(_document(), tmp_path / "b.SchDoc").read_bytes()
    assert first == second


def test_inspector_reads_supplied_reference_files() -> None:
    fixtures = Path(__file__).parent / "fixtures" / "altium"
    empty = AltiumSchDocInspector().records(fixtures / "Empty.SchDoc")
    minimal = AltiumSchDocInspector().records(fixtures / "Minimal.SchDoc")
    assert len(empty) == 29
    assert len(minimal) > len(empty)
    assert 27 in [record.record_type for record in minimal]
    assert 29 in [record.record_type for record in minimal]
