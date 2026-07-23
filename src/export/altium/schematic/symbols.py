from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from .component import SchComponent
from .primitives import SchPoint


class NativeSymbolKind(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    CONNECTOR = "connector"
    IC = "ic"
    GENERIC = "generic"


@dataclass(frozen=True)
class SymbolLine:
    start: SchPoint
    end: SchPoint
    width: int = 1


@dataclass(frozen=True)
class SymbolArc:
    center: SchPoint
    radius_mm: float
    start_angle_deg: float
    end_angle_deg: float
    width: int = 1


@dataclass(frozen=True)
class SymbolRectangle:
    corner_a: SchPoint
    corner_b: SchPoint
    filled: bool = False
    width: int = 1


SymbolPrimitive = SymbolLine | SymbolArc | SymbolRectangle


@dataclass(frozen=True)
class NativeSymbol:
    kind: NativeSymbolKind
    primitives: tuple[SymbolPrimitive, ...]
    body_half_width_mm: float
    body_half_height_mm: float

    def validate(self) -> None:
        if self.body_half_width_mm <= 0 or self.body_half_height_mm <= 0:
            raise ValueError("Native symbol body dimensions must be positive.")
        for primitive in self.primitives:
            if isinstance(primitive, SymbolArc):
                if not isfinite(primitive.radius_mm) or primitive.radius_mm <= 0:
                    raise ValueError("Symbol arc radius must be positive and finite.")


class AltiumSymbolMapper:
    """Resolve logical components to deterministic built-in symbol artwork.

    Mapping prefers explicit symbol/value hints, then the reference prefix. All
    artwork is local to the component origin and is serialized as native Altium
    graphic records by ``AltiumSchDocWriter``.
    """

    def resolve(self, component: SchComponent) -> NativeSymbol:
        kind = self.classify(component)
        symbol = {
            NativeSymbolKind.RESISTOR: self._resistor,
            NativeSymbolKind.CAPACITOR: self._capacitor,
            NativeSymbolKind.INDUCTOR: self._inductor,
            NativeSymbolKind.DIODE: self._diode,
            NativeSymbolKind.CONNECTOR: self._connector,
            NativeSymbolKind.IC: self._ic,
            NativeSymbolKind.GENERIC: self._generic,
        }[kind](component)
        symbol.validate()
        return symbol

    def classify(self, component: SchComponent) -> NativeSymbolKind:
        reference = component.reference.strip().upper()
        hint = " ".join(
            value for value in (
                component.symbol_name,
                component.value,
                component.description or "",
            ) if value
        ).lower()

        if reference.startswith("R") or "resistor" in hint:
            return NativeSymbolKind.RESISTOR
        if reference.startswith("C") or "capacitor" in hint:
            return NativeSymbolKind.CAPACITOR
        if reference.startswith("L") or "inductor" in hint:
            return NativeSymbolKind.INDUCTOR
        if reference.startswith("D") or "diode" in hint:
            return NativeSymbolKind.DIODE
        if reference.startswith(("J", "P", "CN")) or "connector" in hint:
            return NativeSymbolKind.CONNECTOR
        if reference.startswith("U") or any(
            token in hint for token in ("controller", "regulator", "converter", "ic")
        ):
            return NativeSymbolKind.IC
        return NativeSymbolKind.GENERIC

    @staticmethod
    def _p(x: float, y: float) -> SchPoint:
        return SchPoint(x, y)

    def _resistor(self, component: SchComponent) -> NativeSymbol:
        # IEC-style rectangular resistor, horizontal pin axis.
        return NativeSymbol(
            NativeSymbolKind.RESISTOR,
            (
                SymbolLine(self._p(-5.08, 0), self._p(-3.81, 0)),
                SymbolRectangle(self._p(-3.81, -1.27), self._p(3.81, 1.27)),
                SymbolLine(self._p(3.81, 0), self._p(5.08, 0)),
            ),
            3.81,
            1.27,
        )

    def _capacitor(self, component: SchComponent) -> NativeSymbol:
        return NativeSymbol(
            NativeSymbolKind.CAPACITOR,
            (
                SymbolLine(self._p(-5.08, 0), self._p(-0.635, 0)),
                SymbolLine(self._p(-0.635, -2.54), self._p(-0.635, 2.54)),
                SymbolLine(self._p(0.635, -2.54), self._p(0.635, 2.54)),
                SymbolLine(self._p(0.635, 0), self._p(5.08, 0)),
            ),
            1.27,
            2.54,
        )

    def _inductor(self, component: SchComponent) -> NativeSymbol:
        # Four semicircular coils. Native arc records keep the symbol readable.
        return NativeSymbol(
            NativeSymbolKind.INDUCTOR,
            (
                SymbolLine(self._p(-6.35, 0), self._p(-5.08, 0)),
                SymbolArc(self._p(-3.81, 0), 1.27, 180, 0),
                SymbolArc(self._p(-1.27, 0), 1.27, 180, 0),
                SymbolArc(self._p(1.27, 0), 1.27, 180, 0),
                SymbolArc(self._p(3.81, 0), 1.27, 180, 0),
                SymbolLine(self._p(5.08, 0), self._p(6.35, 0)),
            ),
            5.08,
            1.27,
        )

    def _diode(self, component: SchComponent) -> NativeSymbol:
        return NativeSymbol(
            NativeSymbolKind.DIODE,
            (
                SymbolLine(self._p(-5.08, 0), self._p(-2.54, 0)),
                SymbolLine(self._p(-2.54, -2.54), self._p(-2.54, 2.54)),
                SymbolLine(self._p(-2.54, -2.54), self._p(1.27, 0)),
                SymbolLine(self._p(-2.54, 2.54), self._p(1.27, 0)),
                SymbolLine(self._p(1.27, -2.54), self._p(1.27, 2.54)),
                SymbolLine(self._p(1.27, 0), self._p(5.08, 0)),
            ),
            2.54,
            2.54,
        )

    def _connector(self, component: SchComponent) -> NativeSymbol:
        pin_count = max(1, len(component.pins))
        half_h = max(2.54, pin_count * 1.27)
        return NativeSymbol(
            NativeSymbolKind.CONNECTOR,
            (SymbolRectangle(self._p(-2.54, -half_h), self._p(2.54, half_h)),),
            2.54,
            half_h,
        )

    def _ic(self, component: SchComponent) -> NativeSymbol:
        pin_count = max(2, len(component.pins))
        half_h = max(5.08, ((pin_count + 1) // 2) * 1.27)
        return NativeSymbol(
            NativeSymbolKind.IC,
            (SymbolRectangle(self._p(-5.08, -half_h), self._p(5.08, half_h)),),
            5.08,
            half_h,
        )

    def _generic(self, component: SchComponent) -> NativeSymbol:
        half_h = max(3.81, max(1, len(component.pins)) * 1.27)
        return NativeSymbol(
            NativeSymbolKind.GENERIC,
            (SymbolRectangle(self._p(-3.81, -half_h), self._p(3.81, half_h)),),
            3.81,
            half_h,
        )
