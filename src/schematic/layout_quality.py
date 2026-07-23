from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .layout import Point, SchematicLayout, WireSegment


@dataclass(frozen=True)
class LayoutQualityReport:
    wire_length_mm: float
    wire_crossings: int
    component_overlaps: int
    long_wire_count: int
    score: float


class SchematicLayoutScorer:
    """Deterministic quality metrics for schematic layout regression tests."""

    def evaluate(self, layout: SchematicLayout) -> LayoutQualityReport:
        length = sum(
            abs(w.start.x - w.end.x) + abs(w.start.y - w.end.y)
            for w in layout.wires
        )
        crossings = self._crossings(layout.wires)
        overlaps = self._component_overlaps(layout)
        long_wires = sum(
            1
            for w in layout.wires
            if abs(w.start.x - w.end.x) + abs(w.start.y - w.end.y) > 60.0
        )
        score = max(
            0.0,
            100.0
            - crossings * 12.0
            - overlaps * 25.0
            - long_wires * 2.0
            - length / 250.0,
        )
        return LayoutQualityReport(length, crossings, overlaps, long_wires, round(score, 2))

    @staticmethod
    def _component_overlaps(layout: SchematicLayout) -> int:
        symbols = list(layout.symbols.values())
        count = 0
        for i, a in enumerate(symbols):
            for b in symbols[i + 1 :]:
                if (
                    abs(a.position.x - b.position.x) * 2
                    < a.body_width_mm + b.body_width_mm
                    and abs(a.position.y - b.position.y) * 2
                    < a.body_height_mm + b.body_height_mm
                ):
                    count += 1
        return count

    @classmethod
    def _crossings(cls, wires: Iterable[WireSegment]) -> int:
        items = list(wires)
        count = 0
        for i, a in enumerate(items):
            for b in items[i + 1 :]:
                if a.net_name == b.net_name:
                    continue
                if cls._proper_crossing(a, b):
                    count += 1
        return count

    @staticmethod
    def _proper_crossing(a: WireSegment, b: WireSegment) -> bool:
        ah = a.start.y == a.end.y
        bh = b.start.y == b.end.y
        if ah == bh:
            return False
        h, v = (a, b) if ah else (b, a)
        x = v.start.x
        y = h.start.y
        h_min, h_max = sorted((h.start.x, h.end.x))
        v_min, v_max = sorted((v.start.y, v.end.y))
        return h_min < x < h_max and v_min < y < v_max
