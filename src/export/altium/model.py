from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple


class AltiumProjectModelError(Exception):
    """Raised when the Altium intermediate project model is invalid."""


@dataclass(frozen=True)
class AltiumConnection:
    component_reference: str
    pin_number: str

    def validate(self) -> None:
        if not self.component_reference.strip():
            raise AltiumProjectModelError("Connection component_reference cannot be empty.")
        if not self.pin_number.strip():
            raise AltiumProjectModelError("Connection pin_number cannot be empty.")

    def to_dict(self) -> Dict[str, str]:
        return {"component_reference": self.component_reference, "pin_number": self.pin_number}


@dataclass(frozen=True)
class AltiumComponent:
    reference: str
    value: str
    symbol_name: str
    footprint_name: Optional[str] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    fields: Mapping[str, str] = field(default_factory=dict)
    pins: Tuple[Tuple[str, str, str], ...] = ()

    def validate(self) -> None:
        if not self.reference.strip():
            raise AltiumProjectModelError("Component reference cannot be empty.")
        if not self.value.strip():
            raise AltiumProjectModelError(f"Component {self.reference} value cannot be empty.")
        if not self.symbol_name.strip():
            raise AltiumProjectModelError(f"Component {self.reference} symbol_name cannot be empty.")
        seen_numbers: set[str] = set()
        for number, name, electrical_type in self.pins:
            if not number.strip() or not name.strip() or not electrical_type.strip():
                raise AltiumProjectModelError(f"Component {self.reference} contains invalid pin data.")
            if number in seen_numbers:
                raise AltiumProjectModelError(f"Component {self.reference} contains duplicate pin number {number}.")
            seen_numbers.add(number)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference": self.reference,
            "value": self.value,
            "symbol_name": self.symbol_name,
            "footprint_name": self.footprint_name,
            "manufacturer": self.manufacturer,
            "part_number": self.part_number,
            "description": self.description,
            "fields": dict(self.fields),
            "pins": [
                {"number": number, "name": name, "electrical_type": electrical_type}
                for number, name, electrical_type in self.pins
            ],
        }


@dataclass(frozen=True)
class AltiumNet:
    name: str
    connections: Tuple[AltiumConnection, ...]
    net_class: Optional[str] = None
    description: Optional[str] = None

    def validate(self) -> None:
        if not self.name.strip():
            raise AltiumProjectModelError("Net name cannot be empty.")
        if len(self.connections) < 2:
            raise AltiumProjectModelError(f"Net {self.name} must contain at least two connections.")
        seen: set[Tuple[str, str]] = set()
        for connection in self.connections:
            connection.validate()
            key = (connection.component_reference, connection.pin_number)
            if key in seen:
                raise AltiumProjectModelError(
                    f"Net {self.name} contains duplicate connection {connection.component_reference}.{connection.pin_number}."
                )
            seen.add(key)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "net_class": self.net_class,
            "description": self.description,
            "connections": [connection.to_dict() for connection in self.connections],
        }


@dataclass(frozen=True)
class AltiumSymbolPlacement:
    reference: str
    x_mm: float
    y_mm: float
    rotation_deg: int = 0
    body_width_mm: float = 10.16
    body_height_mm: float = 10.16

    def validate(self) -> None:
        if not self.reference.strip():
            raise AltiumProjectModelError("Symbol placement reference cannot be empty.")
        if self.rotation_deg not in {0, 90, 180, 270}:
            raise AltiumProjectModelError(f"Unsupported symbol rotation: {self.rotation_deg}")
        if self.body_width_mm <= 0 or self.body_height_mm <= 0:
            raise AltiumProjectModelError("Symbol body dimensions must be greater than zero.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference": self.reference,
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
            "rotation_deg": self.rotation_deg,
            "body_width_mm": self.body_width_mm,
            "body_height_mm": self.body_height_mm,
        }


@dataclass(frozen=True)
class AltiumWire:
    net_name: str
    start_x_mm: float
    start_y_mm: float
    end_x_mm: float
    end_y_mm: float

    def validate(self) -> None:
        if not self.net_name.strip():
            raise AltiumProjectModelError("Wire net_name cannot be empty.")
        if self.start_x_mm == self.end_x_mm and self.start_y_mm == self.end_y_mm:
            raise AltiumProjectModelError(f"Wire on {self.net_name} has zero length.")
        if self.start_x_mm != self.end_x_mm and self.start_y_mm != self.end_y_mm:
            raise AltiumProjectModelError(f"Wire on {self.net_name} is not orthogonal.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "net_name": self.net_name,
            "start": {"x_mm": self.start_x_mm, "y_mm": self.start_y_mm},
            "end": {"x_mm": self.end_x_mm, "y_mm": self.end_y_mm},
        }


@dataclass
class AltiumProjectModel:
    project_name: str
    design_name: str
    grid_mm: float
    components: List[AltiumComponent] = field(default_factory=list)
    nets: List[AltiumNet] = field(default_factory=list)
    placements: List[AltiumSymbolPlacement] = field(default_factory=list)
    wires: List[AltiumWire] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"

    def validate(self) -> None:
        if not self.project_name.strip():
            raise AltiumProjectModelError("project_name cannot be empty.")
        if not self.design_name.strip():
            raise AltiumProjectModelError("design_name cannot be empty.")
        if self.grid_mm <= 0:
            raise AltiumProjectModelError("grid_mm must be greater than zero.")
        refs: set[str] = set()
        pins_by_ref: Dict[str, set[str]] = {}
        for component in self.components:
            component.validate()
            if component.reference in refs:
                raise AltiumProjectModelError(f"Duplicate component reference: {component.reference}")
            refs.add(component.reference)
            pins_by_ref[component.reference] = {pin[0] for pin in component.pins}
        placement_refs: set[str] = set()
        for placement in self.placements:
            placement.validate()
            if placement.reference in placement_refs:
                raise AltiumProjectModelError(f"Duplicate placement reference: {placement.reference}")
            if placement.reference not in refs:
                raise AltiumProjectModelError(f"Placement references unknown component: {placement.reference}")
            placement_refs.add(placement.reference)
        missing = refs - placement_refs
        if missing:
            raise AltiumProjectModelError("Missing placements: " + ", ".join(sorted(missing)))
        net_names: set[str] = set()
        for net in self.nets:
            net.validate()
            if net.name in net_names:
                raise AltiumProjectModelError(f"Duplicate net name: {net.name}")
            net_names.add(net.name)
            for connection in net.connections:
                pin_numbers = pins_by_ref.get(connection.component_reference)
                if pin_numbers is None:
                    raise AltiumProjectModelError(
                        f"Net {net.name} references unknown component {connection.component_reference}."
                    )
                if connection.pin_number not in pin_numbers:
                    raise AltiumProjectModelError(
                        f"Net {net.name} references unknown pin {connection.component_reference}.{connection.pin_number}."
                    )
        for wire in self.wires:
            wire.validate()
            if wire.net_name not in net_names:
                raise AltiumProjectModelError(f"Wire references unknown net: {wire.net_name}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "schema": "llm-pcb.altium-intermediate-project",
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "design_name": self.design_name,
            "grid_mm": self.grid_mm,
            "metadata": dict(self.metadata),
            "components": [component.to_dict() for component in self.components],
            "nets": [net.to_dict() for net in self.nets],
            "placements": [placement.to_dict() for placement in self.placements],
            "wires": [wire.to_dict() for wire in self.wires],
        }
