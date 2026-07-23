from __future__ import annotations

from pathlib import Path

from src.export.altium.schematic import (
    AltiumSchDocInspector,
    AltiumSchDocWriter,
    AltiumSchematicDocument,
    SchComponent,
    SchPoint,
    SchSheet,
)


def test_native_writer_emits_symbol_graphic_records(tmp_path: Path) -> None:
    document = AltiumSchematicDocument(
        document_id="phase16d",
        name="Symbols",
        sheet=SchSheet(name="Symbols"),
        components=(
            SchComponent("r1", "R1", "10k", "Device:R", SchPoint(20, 20)),
            SchComponent("c1", "C1", "1uF", "Device:C", SchPoint(40, 20)),
            SchComponent("l1", "L1", "10uH", "Device:L", SchPoint(60, 20)),
        ),
    )
    path = AltiumSchDocWriter().write(document, tmp_path / "Symbols.SchDoc")
    records = AltiumSchDocInspector().records(path)
    record_ids = [record.record_type for record in records]
    assert 13 in record_ids  # line
    assert 14 in record_ids  # rectangle
    assert 12 in record_ids  # arc
