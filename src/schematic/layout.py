from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .model import (
    PinReference,
    SchematicComponent,
    SchematicDesign,
)


class SchematicLayoutError(Exception):
    """Raised when a schematic layout cannot be generated safely."""


@dataclass(frozen=True)
class Point:
    """Two-dimensional schematic coordinate in millimetres."""

    x: float
    y: float

    def snapped(self, grid_mm: float) -> "Point":
        if grid_mm <= 0:
            raise SchematicLayoutError(
                "grid_mm must be greater than zero."
            )

        return Point(
            x=round(self.x / grid_mm) * grid_mm,
            y=round(self.y / grid_mm) * grid_mm,
        )


@dataclass(frozen=True)
class SymbolLayout:
    """Placement of one schematic component."""

    reference: str
    position: Point
    rotation_deg: int = 0
    body_width_mm: float = 10.16
    body_height_mm: float = 10.16

    def validate(self) -> None:
        if not self.reference.strip():
            raise SchematicLayoutError(
                "SymbolLayout reference cannot be empty."
            )

        if self.rotation_deg not in {0, 90, 180, 270}:
            raise SchematicLayoutError(
                f"Unsupported symbol rotation: {self.rotation_deg}"
            )

        if self.body_width_mm <= 0 or self.body_height_mm <= 0:
            raise SchematicLayoutError(
                "Symbol body dimensions must be greater than zero."
            )


@dataclass(frozen=True)
class PinLayout:
    """Absolute endpoint of one symbol pin."""

    component_reference: str
    pin_number: str
    endpoint: Point

    def validate(self) -> None:
        if not self.component_reference.strip():
            raise SchematicLayoutError(
                "PinLayout component_reference cannot be empty."
            )

        if not self.pin_number.strip():
            raise SchematicLayoutError(
                "PinLayout pin_number cannot be empty."
            )


@dataclass(frozen=True)
class WireSegment:
    """Visible orthogonal wire segment."""

    net_name: str
    start: Point
    end: Point

    def validate(self) -> None:
        if not self.net_name.strip():
            raise SchematicLayoutError(
                "WireSegment net_name cannot be empty."
            )

        if self.start == self.end:
            raise SchematicLayoutError(
                f"WireSegment on {self.net_name} has zero length."
            )

        if (
            abs(self.start.x - self.end.x) > 1e-9
            and abs(self.start.y - self.end.y) > 1e-9
        ):
            raise SchematicLayoutError(
                f"WireSegment on {self.net_name} is not orthogonal."
            )


@dataclass(frozen=True)
class Junction:
    """Connection point where multiple wire segments meet."""

    net_name: str
    position: Point


@dataclass(frozen=True)
class NetLabelLayout:
    """Graphical placement of one net label."""

    net_name: str
    position: Point
    rotation_deg: int = 0


@dataclass
class SchematicLayout:
    """Technology-neutral graphical layout for a schematic."""

    design_name: str
    grid_mm: float
    symbols: Dict[str, SymbolLayout] = field(default_factory=dict)
    pins: Dict[Tuple[str, str], PinLayout] = field(default_factory=dict)
    wires: List[WireSegment] = field(default_factory=list)
    junctions: List[Junction] = field(default_factory=list)
    labels: List[NetLabelLayout] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def add_symbol(self, symbol: SymbolLayout) -> None:
        symbol.validate()

        if symbol.reference in self.symbols:
            raise SchematicLayoutError(
                f"Duplicate symbol layout: {symbol.reference}"
            )

        self.symbols[symbol.reference] = symbol

    def add_pin(self, pin: PinLayout) -> None:
        pin.validate()

        key = (
            pin.component_reference,
            pin.pin_number,
        )

        if key in self.pins:
            raise SchematicLayoutError(
                f"Duplicate pin layout: "
                f"{pin.component_reference}.{pin.pin_number}"
            )

        self.pins[key] = pin

    def add_wire(self, wire: WireSegment) -> None:
        wire.validate()

        if wire not in self.wires:
            self.wires.append(wire)

    def add_junction(self, junction: Junction) -> None:
        if junction not in self.junctions:
            self.junctions.append(junction)

    def add_label(self, label: NetLabelLayout) -> None:
        if label not in self.labels:
            self.labels.append(label)

    def get_symbol(self, reference: str) -> SymbolLayout:
        try:
            return self.symbols[reference]
        except KeyError as exc:
            raise KeyError(
                f"Unknown symbol layout: {reference}"
            ) from exc

    def get_pin(
        self,
        component_reference: str,
        pin_number: str,
    ) -> PinLayout:
        key = (component_reference, pin_number)

        try:
            return self.pins[key]
        except KeyError as exc:
            raise KeyError(
                f"Unknown pin layout: "
                f"{component_reference}.{pin_number}"
            ) from exc

    def wires_for_net(self, net_name: str) -> List[WireSegment]:
        return [
            wire
            for wire in self.wires
            if wire.net_name == net_name
        ]

    def validate(self, design: SchematicDesign) -> None:
        design.validate()

        if self.grid_mm <= 0:
            raise SchematicLayoutError(
                "SchematicLayout grid_mm must be greater than zero."
            )

        design_references = {
            component.reference
            for component in design.components
        }

        layout_references = set(self.symbols)

        missing_symbols = design_references - layout_references
        if missing_symbols:
            raise SchematicLayoutError(
                "Missing symbol layouts: "
                + ", ".join(sorted(missing_symbols))
            )

        extra_symbols = layout_references - design_references
        if extra_symbols:
            raise SchematicLayoutError(
                "Layout contains unknown symbols: "
                + ", ".join(sorted(extra_symbols))
            )

        for component in design.components:
            for pin in component.pins:
                key = (component.reference, pin.number)

                if key not in self.pins:
                    raise SchematicLayoutError(
                        f"Missing pin layout: "
                        f"{component.reference}.{pin.number}"
                    )

        expected_nets = {net.name for net in design.nets}
        wire_nets = {wire.net_name for wire in self.wires}

        unknown_wire_nets = wire_nets - expected_nets
        if unknown_wire_nets:
            raise SchematicLayoutError(
                "Wires reference unknown nets: "
                + ", ".join(sorted(unknown_wire_nets))
            )

        for wire in self.wires:
            wire.validate()

        for net in design.nets:
            endpoints = {
                self.get_pin(
                    connection.component_reference,
                    connection.pin_number,
                ).endpoint
                for connection in net.connections
            }

            if len(endpoints) < 2:
                raise SchematicLayoutError(
                    f"Net {net.name} has fewer than two distinct endpoints."
                )

            if not self.wires_for_net(net.name):
                raise SchematicLayoutError(
                    f"Net {net.name} has no visible wires."
                )

    def to_dict(self) -> Dict[str, object]:
        return {
            "design_name": self.design_name,
            "grid_mm": self.grid_mm,
            "metadata": dict(self.metadata),
            "symbols": {
                reference: {
                    "x": symbol.position.x,
                    "y": symbol.position.y,
                    "rotation_deg": symbol.rotation_deg,
                    "body_width_mm": symbol.body_width_mm,
                    "body_height_mm": symbol.body_height_mm,
                }
                for reference, symbol in self.symbols.items()
            },
            "pins": [
                {
                    "component_reference": pin.component_reference,
                    "pin_number": pin.pin_number,
                    "x": pin.endpoint.x,
                    "y": pin.endpoint.y,
                }
                for pin in self.pins.values()
            ],
            "wires": [
                {
                    "net_name": wire.net_name,
                    "start": {
                        "x": wire.start.x,
                        "y": wire.start.y,
                    },
                    "end": {
                        "x": wire.end.x,
                        "y": wire.end.y,
                    },
                }
                for wire in self.wires
            ],
            "junctions": [
                {
                    "net_name": junction.net_name,
                    "x": junction.position.x,
                    "y": junction.position.y,
                }
                for junction in self.junctions
            ],
            "labels": [
                {
                    "net_name": label.net_name,
                    "x": label.position.x,
                    "y": label.position.y,
                    "rotation_deg": label.rotation_deg,
                }
                for label in self.labels
            ],
        }


class BuckSchematicLayoutEngine:
    """
    Generate a readable orthogonal schematic layout for a Buck converter.

    The engine is independent of KiCad and Altium file formats.
    """

    DEFAULT_GRID_MM = 2.54

    DEFAULT_POSITIONS: Mapping[str, Point] = {
        "J1": Point(25.4, 76.2),
        "CIN": Point(50.8, 88.9),
        "U1": Point(88.9, 76.2),
        "CBOOT": Point(101.6, 48.26),
        "L1": Point(127.0, 76.2),
        "COUT": Point(152.4, 88.9),
        "R1": Point(177.8, 76.2),
        "R2": Point(177.8, 101.6),
        "J2": Point(215.9, 76.2),
    }

    NET_TRUNK_Y: Mapping[str, float] = {
        "BOOT": 43.18,
        "VIN": 63.50,
        "SW": 71.12,
        "VOUT": 78.74,
        "FB": 91.44,
        "GND": 111.76,
    }

    def __init__(
        self,
        grid_mm: float = DEFAULT_GRID_MM,
    ) -> None:
        if grid_mm <= 0:
            raise SchematicLayoutError(
                "grid_mm must be greater than zero."
            )

        self.grid_mm = grid_mm

    def layout(
        self,
        design: SchematicDesign,
        symbol_positions: Optional[Mapping[str, Point]] = None,
    ) -> SchematicLayout:
        design.validate()

        positions = dict(self.DEFAULT_POSITIONS)
        if symbol_positions:
            positions.update(symbol_positions)

        missing = [
            component.reference
            for component in design.components
            if component.reference not in positions
        ]

        if missing:
            raise SchematicLayoutError(
                "Missing Buck schematic positions for: "
                + ", ".join(sorted(missing))
            )

        result = SchematicLayout(
            design_name=design.name,
            grid_mm=self.grid_mm,
            metadata={
                "topology": "buck",
                "layout_engine": (
                    self.__class__.__name__
                ),
            },
        )

        for component in design.components:
            position = positions[
                component.reference
            ].snapped(self.grid_mm)

            width, height = self._component_body_size(component)

            result.add_symbol(
                SymbolLayout(
                    reference=component.reference,
                    position=position,
                    rotation_deg=0,
                    body_width_mm=width,
                    body_height_mm=height,
                )
            )

            pin_offsets = self._pin_offsets(component)

            for pin in component.pins:
                offset = pin_offsets[pin.number]

                result.add_pin(
                    PinLayout(
                        component_reference=component.reference,
                        pin_number=pin.number,
                        endpoint=Point(
                            position.x + offset.x,
                            position.y + offset.y,
                        ).snapped(self.grid_mm),
                    )
                )

        for net_index, net in enumerate(design.nets):
            self._route_net(
                layout=result,
                design=design,
                net_name=net.name,
                connections=net.connections,
                net_index=net_index,
            )

        result.validate(design)
        return result

    def _route_net(
        self,
        layout: SchematicLayout,
        design: SchematicDesign,
        net_name: str,
        connections: Sequence[PinReference],
        net_index: int,
    ) -> None:
        endpoints = [
            layout.get_pin(
                connection.component_reference,
                connection.pin_number,
            ).endpoint
            for connection in connections
        ]

        if len(endpoints) < 2:
            raise SchematicLayoutError(
                f"Net {net_name} has too few endpoints."
            )

        trunk_y = self._net_trunk_y(
            net_name,
            endpoints,
            net_index,
        )

        min_x = min(point.x for point in endpoints)
        max_x = max(point.x for point in endpoints)

        trunk_start = Point(
            min_x - self.grid_mm,
            trunk_y,
        ).snapped(self.grid_mm)

        trunk_end = Point(
            max_x + self.grid_mm,
            trunk_y,
        ).snapped(self.grid_mm)

        layout.add_wire(
            WireSegment(
                net_name=net_name,
                start=trunk_start,
                end=trunk_end,
            )
        )

        branch_positions: Dict[Point, int] = {}

        for endpoint in endpoints:
            branch_point = Point(
                endpoint.x,
                trunk_y,
            ).snapped(self.grid_mm)

            if endpoint != branch_point:
                layout.add_wire(
                    WireSegment(
                        net_name=net_name,
                        start=endpoint,
                        end=branch_point,
                    )
                )

            branch_positions[branch_point] = (
                branch_positions.get(branch_point, 0) + 1
            )

        for branch_point in branch_positions:
            layout.add_junction(
                Junction(
                    net_name=net_name,
                    position=branch_point,
                )
            )

        layout.add_label(
            NetLabelLayout(
                net_name=net_name,
                position=trunk_start,
                rotation_deg=0,
            )
        )

    def _net_trunk_y(
        self,
        net_name: str,
        endpoints: Sequence[Point],
        net_index: int,
    ) -> float:
        preferred = self.NET_TRUNK_Y.get(net_name.upper())

        if preferred is not None:
            return Point(
                0.0,
                preferred,
            ).snapped(self.grid_mm).y

        average_y = (
            sum(point.y for point in endpoints)
            / len(endpoints)
        )

        return Point(
            0.0,
            average_y + net_index * self.grid_mm,
        ).snapped(self.grid_mm).y

    def _pin_offsets(
        self,
        component: SchematicComponent,
    ) -> Dict[str, Point]:
        if component.reference.startswith(("C", "R")):
            self._require_pin_count(component, 2)

            return {
                component.pins[0].number: Point(
                    0.0,
                    -5.08,
                ),
                component.pins[1].number: Point(
                    0.0,
                    5.08,
                ),
            }

        if component.reference.startswith("L"):
            self._require_pin_count(component, 2)

            return {
                component.pins[0].number: Point(
                    -7.62,
                    0.0,
                ),
                component.pins[1].number: Point(
                    7.62,
                    0.0,
                ),
            }

        if component.reference.startswith("J"):
            return self._connector_pin_offsets(component)

        if component.reference.startswith("U"):
            return self._regulator_pin_offsets(component)

        raise SchematicLayoutError(
            f"Unsupported component type: "
            f"{component.reference}"
        )

    def _connector_pin_offsets(
        self,
        component: SchematicComponent,
    ) -> Dict[str, Point]:
        count = len(component.pins)

        if count < 1:
            raise SchematicLayoutError(
                f"{component.reference} has no pins."
            )

        start_y = -(
            (count - 1)
            * self.grid_mm
            / 2.0
        )

        return {
            pin.number: Point(
                5.08,
                start_y + index * self.grid_mm,
            ).snapped(self.grid_mm)
            for index, pin in enumerate(component.pins)
        }

    def _regulator_pin_offsets(
        self,
        component: SchematicComponent,
    ) -> Dict[str, Point]:
        named = {
            pin.name.strip().upper(): pin
            for pin in component.pins
        }

        offsets: Dict[str, Point] = {}

        desired = {
            "VIN": Point(-10.16, -5.08),
            "EN": Point(-10.16, 0.0),
            "FB": Point(-10.16, 5.08),
            "BOOT": Point(10.16, -5.08),
            "SW": Point(10.16, 0.0),
            "GND": Point(0.0, 10.16),
        }

        for pin_name, offset in desired.items():
            pin = named.get(pin_name)

            if pin is not None:
                offsets[pin.number] = offset.snapped(
                    self.grid_mm
                )

        unassigned = [
            pin
            for pin in component.pins
            if pin.number not in offsets
        ]

        for index, pin in enumerate(unassigned):
            offsets[pin.number] = Point(
                -10.16,
                10.16 + index * self.grid_mm,
            ).snapped(self.grid_mm)

        return offsets

    @staticmethod
    def _component_body_size(
        component: SchematicComponent,
    ) -> Tuple[float, float]:
        if component.reference.startswith("U"):
            return 15.24, 15.24

        if component.reference.startswith("J"):
            return 7.62, max(
                7.62,
                len(component.pins) * 2.54,
            )

        if component.reference.startswith("L"):
            return 10.16, 5.08

        return 5.08, 5.08

    @staticmethod
    def _require_pin_count(
        component: SchematicComponent,
        expected: int,
    ) -> None:
        if len(component.pins) != expected:
            raise SchematicLayoutError(
                f"{component.reference} must have "
                f"exactly {expected} pins."
            )
