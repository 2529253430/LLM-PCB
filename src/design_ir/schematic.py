from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Tuple

from .geometry import IRPoint, IRSegment, IRSize


@dataclass(frozen=True)
class IRSymbolPlacement:
    """Placement of one schematic component symbol."""

    component_id: str
    position: IRPoint
    body_size: IRSize
    rotation_deg: int = 0
    mirrored: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.component_id.strip():
            raise ValueError(
                "IRSymbolPlacement component_id cannot be empty."
            )
        if self.rotation_deg not in {0, 90, 180, 270}:
            raise ValueError(
                f"Unsupported symbol rotation: {self.rotation_deg}"
            )
        self.body_size.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "component_id": self.component_id,
            "position": self.position.to_dict(),
            "body_size": self.body_size.to_dict(),
            "rotation_deg": self.rotation_deg,
            "mirrored": self.mirrored,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class IRPinPlacement:
    """Absolute endpoint of one schematic pin."""

    component_id: str
    pin_number: str
    endpoint: IRPoint

    def validate(self) -> None:
        if not self.component_id.strip():
            raise ValueError(
                "IRPinPlacement component_id cannot be empty."
            )
        if not self.pin_number.strip():
            raise ValueError(
                "IRPinPlacement pin_number cannot be empty."
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "component_id": self.component_id,
            "pin_number": self.pin_number,
            "endpoint": self.endpoint.to_dict(),
        }


@dataclass(frozen=True)
class IRWire:
    """Visible schematic wire assigned to a logical net."""

    net_id: str
    segment: IRSegment
    style: str = "default"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self, *, require_orthogonal: bool = True) -> None:
        if not self.net_id.strip():
            raise ValueError("IRWire net_id cannot be empty.")
        if self.segment.is_zero_length:
            raise ValueError(
                f"IRWire on {self.net_id} has zero length."
            )
        if require_orthogonal and not self.segment.is_orthogonal:
            raise ValueError(
                f"IRWire on {self.net_id} is not orthogonal."
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "net_id": self.net_id,
            "segment": self.segment.to_dict(),
            "style": self.style,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class IRJunction:
    """Schematic junction assigned to one net."""

    net_id: str
    position: IRPoint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "net_id": self.net_id,
            "position": self.position.to_dict(),
        }


@dataclass(frozen=True)
class IRNetLabel:
    """Visible schematic net label."""

    net_id: str
    position: IRPoint
    text: str
    rotation_deg: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "net_id": self.net_id,
            "position": self.position.to_dict(),
            "text": self.text,
            "rotation_deg": self.rotation_deg,
        }


@dataclass(frozen=True)
class IRSchematic:
    """Technology-neutral schematic geometry."""

    name: str
    grid_mm: float
    symbol_placements: Tuple[IRSymbolPlacement, ...] = ()
    pin_placements: Tuple[IRPinPlacement, ...] = ()
    wires: Tuple[IRWire, ...] = ()
    junctions: Tuple[IRJunction, ...] = ()
    labels: Tuple[IRNetLabel, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate_local(self) -> None:
        if not self.name.strip():
            raise ValueError("IRSchematic name cannot be empty.")
        if self.grid_mm <= 0:
            raise ValueError(
                "IRSchematic grid_mm must be greater than zero."
            )
        for placement in self.symbol_placements:
            placement.validate()
        for placement in self.pin_placements:
            placement.validate()
        for wire in self.wires:
            wire.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate_local()
        return {
            "name": self.name,
            "grid_mm": self.grid_mm,
            "metadata": dict(self.metadata),
            "symbol_placements": [
                placement.to_dict()
                for placement in self.symbol_placements
            ],
            "pin_placements": [
                placement.to_dict()
                for placement in self.pin_placements
            ],
            "wires": [wire.to_dict() for wire in self.wires],
            "junctions": [
                junction.to_dict()
                for junction in self.junctions
            ],
            "labels": [label.to_dict() for label in self.labels],
        }
