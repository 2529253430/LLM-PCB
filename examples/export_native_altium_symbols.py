from __future__ import annotations

from src.export.altium.schematic import (
    AltiumSchDocWriter,
    AltiumSchematicDocument,
    SchComponent,
    SchPoint,
    SchSheet,
)


def main() -> None:
    references = ("R1", "C1", "L1", "D1", "J1", "U1")
    components = tuple(
        SchComponent(
            component_id=f"symbol:{reference}",
            reference=reference,
            value=reference,
            symbol_name="LLM-PCB Builtin",
            location=SchPoint(20.0 + index * 20.0, 40.0),
        )
        for index, reference in enumerate(references)
    )
    document = AltiumSchematicDocument(
        document_id="phase16d-symbol-gallery",
        name="Phase16D Symbols",
        sheet=SchSheet(name="Phase16D Symbols"),
        components=components,
    )
    output = AltiumSchDocWriter().write(
        document,
        "output/altium_phase16d/Phase16D_Symbols.SchDoc",
    )
    print(output)


if __name__ == "__main__":
    main()
