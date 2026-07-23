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
    """Generate a readable, topology-aware Buck schematic layout.

    Phase 16E.2 uses explicit power-stage, feedback, bootstrap, and return
    channels instead of routing every net through one global horizontal bus.
    """

    DEFAULT_GRID_MM = 2.54
    DEFAULT_POSITIONS: Mapping[str, Point] = {
        "J1": Point(25.4, 76.2),
        "CIN": Point(50.8, 71.12),
        "U1": Point(86.36, 76.2),
        "CBOOT": Point(111.76, 86.36),
        "L1": Point(132.08, 76.2),
        "COUT": Point(160.02, 71.12),
        "R1": Point(187.96, 71.12),
        "R2": Point(187.96, 55.88),
        "J2": Point(220.98, 76.2),
    }

    POWER_PATH_Y = 76.2
    FEEDBACK_Y = 63.5
    GROUND_Y = 45.72

    def __init__(self, grid_mm: float = DEFAULT_GRID_MM) -> None:
        if grid_mm <= 0:
            raise SchematicLayoutError("grid_mm must be greater than zero.")
        self.grid_mm = grid_mm

    def layout(self, design: SchematicDesign,
               symbol_positions: Optional[Mapping[str, Point]] = None) -> SchematicLayout:
        design.validate()
        positions = dict(self.DEFAULT_POSITIONS)
        if symbol_positions:
            positions.update(symbol_positions)
        missing = [c.reference for c in design.components if c.reference not in positions]
        if missing:
            raise SchematicLayoutError("Missing Buck schematic positions for: " + ", ".join(sorted(missing)))

        result = SchematicLayout(
            design_name=design.name,
            grid_mm=self.grid_mm,
            metadata={
                "topology": "buck",
                "layout_engine": self.__class__.__name__,
                "layout_strategy": "topology_aware_signal_flow",
                "optimization_revision": "local_channels_v2",
                "layout_phase": "16E",
            },
        )
        for component in design.components:
            position = positions[component.reference].snapped(self.grid_mm)
            width, height = self._component_body_size(component)
            result.add_symbol(SymbolLayout(component.reference, position, 0, width, height))
            offsets = self._pin_offsets(component)
            for pin in component.pins:
                off = offsets[pin.number]
                result.add_pin(PinLayout(component.reference, pin.number,
                                         Point(position.x + off.x, position.y + off.y).snapped(self.grid_mm)))

        for net in design.nets:
            self._route_named_net(result, net.name, net.connections)
        result.validate(design)
        return result

    def _route_named_net(self, layout: SchematicLayout, net_name: str,
                         connections: Sequence[PinReference]) -> None:
        endpoints: Dict[str, List[Point]] = {}
        for connection in connections:
            endpoints.setdefault(connection.component_reference, []).append(
                layout.get_pin(connection.component_reference, connection.pin_number).endpoint
            )
        name = net_name.upper()
        if name == "VIN":
            self._route_vin(layout, net_name, endpoints)
        elif name == "SW":
            self._route_sw(layout, net_name, endpoints)
        elif name == "VOUT":
            self._route_vout(layout, net_name, endpoints)
        elif name == "FB":
            self._route_fb(layout, net_name, endpoints)
        elif name == "BOOT":
            self._route_boot(layout, net_name, endpoints)
        elif name == "GND":
            self._route_gnd(layout, net_name, endpoints)
        else:
            self._route_tree(layout, net_name, [p for values in endpoints.values() for p in values])

    @staticmethod
    def _first(endpoints: Mapping[str, List[Point]], reference: str) -> Optional[Point]:
        points = endpoints.get(reference, [])
        return points[0] if points else None

    def _attach_to_lane(self, l: SchematicLayout, n: str, p: Point,
                        lane_y: float, junction: bool = True) -> Point:
        tap = Point(p.x, lane_y).snapped(self.grid_mm)
        self._add_segment(l, n, p, tap)
        if junction and p != tap:
            l.add_junction(Junction(n, tap))
        return tap

    def _route_vin(self, l, n, e):
        j = self._first(e, "J1")
        u_points = e.get("U1", [])
        u = max(u_points, key=lambda p: p.y) if u_points else None
        lane_y = Point(0, self.POWER_PATH_Y).snapped(self.grid_mm).y
        taps = [self._attach_to_lane(l, n, p, lane_y) for p in [j, u] if p]
        cin = self._first(e, "CIN")
        if cin: taps.append(self._attach_to_lane(l, n, cin, lane_y))
        if taps: self._add_segment(l, n, Point(min(p.x for p in taps), lane_y), Point(max(p.x for p in taps), lane_y))
        # EN gets a short local tie to the VIN pin.
        for p in u_points:
            if p != u and u:
                x = min(p.x, u.x) - 2 * self.grid_mm
                self._add_segment(l, n, p, Point(x, p.y))
                self._add_segment(l, n, Point(x, p.y), Point(x, u.y))
                self._add_segment(l, n, Point(x, u.y), u)
        self._label(l, n, Point(min(p.x for p in taps), lane_y), dy=self.grid_mm)

    def _route_sw(self, l, n, e):
        u = self._first(e, "U1"); ind = self._first(e, "L1")
        lane_y = Point(0, self.POWER_PATH_Y).snapped(self.grid_mm).y
        taps=[self._attach_to_lane(l,n,p,lane_y) for p in (u,ind) if p]
        if taps: self._add_segment(l,n,Point(min(p.x for p in taps),lane_y),Point(max(p.x for p in taps),lane_y))
        boot = self._first(e,"CBOOT")
        if boot:
            tap=self._attach_to_lane(l,n,boot,lane_y); l.add_junction(Junction(n,tap))
        self._label(l,n,u or ind,dy=self.grid_mm)

    def _route_vout(self, l, n, e):
        lane_y = Point(0, self.POWER_PATH_Y).snapped(self.grid_mm).y
        refs=("L1","COUT","R1","J2")
        taps=[]
        for ref in refs:
            p=self._first(e,ref)
            if p: taps.append(self._attach_to_lane(l,n,p,lane_y))
        if taps: self._add_segment(l,n,Point(min(p.x for p in taps),lane_y),Point(max(p.x for p in taps),lane_y))
        self._label(l,n,Point(min(p.x for p in taps),lane_y),dy=self.grid_mm)

    def _route_fb(self, l, n, e):
        u=self._first(e,"U1"); r1=self._first(e,"R1"); r2=self._first(e,"R2")
        divider_points=[p for p in (r1,r2) if p]
        if not divider_points: return
        node=Point(divider_points[0].x, self.FEEDBACK_Y).snapped(self.grid_mm)
        for p in divider_points: self._add_segment(l,n,p,node)
        if u:
            self._add_segment(l,n,u,Point(node.x,u.y)); self._add_segment(l,n,Point(node.x,u.y),node)
        l.add_junction(Junction(n,node)); self._label(l,n,u or node,dy=self.grid_mm)

    def _route_boot(self, l, n, e):
        u=self._first(e,"U1"); c=self._first(e,"CBOOT")
        if u and c:
            corner=Point(c.x,u.y); self._add_segment(l,n,u,corner); self._add_segment(l,n,corner,c)
        self._label(l,n,u or c,dy=self.grid_mm)

    def _route_gnd(self, l, n, e):
        y=Point(0,self.GROUND_Y).snapped(self.grid_mm).y
        points=[p for values in e.values() for p in values]
        taps=[self._attach_to_lane(l,n,p,y) for p in points]
        self._add_segment(l,n,Point(min(p.x for p in taps),y),Point(max(p.x for p in taps),y))
        self._label(l,n,Point(min(p.x for p in taps),y),dy=self.grid_mm)

    def _route_tree(self,l,n,endpoints):
        ordered=sorted(endpoints,key=lambda p:(p.x,p.y)); anchor=ordered[0]
        for p in ordered[1:]:
            c=Point(p.x,anchor.y); self._add_segment(l,n,anchor,c); self._add_segment(l,n,c,p)
        self._label(l,n,anchor,dy=self.grid_mm)

    def _label(self,l,n,p,dy=0.0):
        if p is not None: l.add_label(NetLabelLayout(n,Point(p.x,p.y+dy).snapped(self.grid_mm),0))

    @staticmethod
    def _add_segment(layout,net_name,start,end):
        if start!=end: layout.add_wire(WireSegment(net_name,start,end))

    def _pin_offsets(self, component: SchematicComponent) -> Dict[str, Point]:
        ref=component.reference.upper()
        if ref.startswith(("C","R")):
            self._require_pin_count(component,2)
            return {component.pins[0].number:Point(0,5.08), component.pins[1].number:Point(0,-5.08)}
        if ref.startswith("L"):
            self._require_pin_count(component,2)
            return {component.pins[0].number:Point(-7.62,0), component.pins[1].number:Point(7.62,0)}
        if ref.startswith("J"):
            side=5.08 if ref=="J1" else -5.08
            return {component.pins[0].number:Point(side,5.08), component.pins[1].number:Point(side,-5.08)}
        if ref.startswith("U"):
            named={p.name.strip().upper():p for p in component.pins}
            desired={"VIN":Point(-10.16,0),"EN":Point(-10.16,-5.08),"SW":Point(10.16,0),"BOOT":Point(10.16,5.08),"FB":Point(10.16,-5.08),"GND":Point(0,-10.16)}
            offsets={named[k].number:v for k,v in desired.items() if k in named}
            for i,p in enumerate([p for p in component.pins if p.number not in offsets]): offsets[p.number]=Point(-10.16,-10.16-i*self.grid_mm)
            return offsets
        raise SchematicLayoutError(f"Unsupported component type: {component.reference}")

    @staticmethod
    def _component_body_size(component):
        ref=component.reference.upper()
        if ref.startswith("U"): return 15.24,20.32
        if ref.startswith("J"): return 7.62,max(12.7,len(component.pins)*5.08)
        if ref.startswith("L"): return 10.16,5.08
        return 5.08,7.62

    @staticmethod
    def _require_pin_count(component,expected):
        if len(component.pins)!=expected: raise SchematicLayoutError(f"{component.reference} must have exactly {expected} pins.")
