from __future__ import annotations

from src.export.altium.schematic import (
    AltiumSymbolMapper,
    NativeSymbolKind,
    SchComponent,
    SchPoint,
    SymbolArc,
    SymbolLine,
    SymbolRectangle,
)


def _component(reference: str, symbol_name: str = "Device") -> SchComponent:
    return SchComponent(
        component_id=f"component:{reference}",
        reference=reference,
        value="value",
        symbol_name=symbol_name,
        location=SchPoint(10.0, 20.0),
    )


def test_reference_prefix_mapping() -> None:
    mapper = AltiumSymbolMapper()
    expected = {
        "R1": NativeSymbolKind.RESISTOR,
        "C1": NativeSymbolKind.CAPACITOR,
        "L1": NativeSymbolKind.INDUCTOR,
        "D1": NativeSymbolKind.DIODE,
        "J1": NativeSymbolKind.CONNECTOR,
        "U1": NativeSymbolKind.IC,
    }
    for reference, kind in expected.items():
        assert mapper.resolve(_component(reference)).kind is kind


def test_resistor_uses_native_lines_and_rectangle() -> None:
    symbol = AltiumSymbolMapper().resolve(_component("R1"))
    assert sum(isinstance(p, SymbolLine) for p in symbol.primitives) == 2
    assert sum(isinstance(p, SymbolRectangle) for p in symbol.primitives) == 1


def test_capacitor_uses_two_plate_lines() -> None:
    symbol = AltiumSymbolMapper().resolve(_component("CIN"))
    assert symbol.kind is NativeSymbolKind.CAPACITOR
    assert len(symbol.primitives) == 4
    assert all(isinstance(p, SymbolLine) for p in symbol.primitives)


def test_inductor_uses_native_arcs() -> None:
    symbol = AltiumSymbolMapper().resolve(_component("L1"))
    assert sum(isinstance(p, SymbolArc) for p in symbol.primitives) == 4


def test_symbol_hint_is_used_when_reference_is_generic() -> None:
    symbol = AltiumSymbolMapper().resolve(
        _component("X1", "Device:Resistor")
    )
    assert symbol.kind is NativeSymbolKind.RESISTOR
