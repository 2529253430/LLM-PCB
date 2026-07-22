from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .primitives import (
    AltiumSchematicModelError,
    SchPoint,
    normalize_rotation,
)


class SchPinElectricalType(str, Enum):
    PASSIVE = "passive"
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    POWER = "power"
    OPEN_COLLECTOR = "open_collector"
    OPEN_EMITTER = "open_emitter"
    TRI_STATE = "tri_state"
    UNSPECIFIED = "unspecified"


@dataclass(frozen=True)
class SchPin:
    pin_id: str
    name: str
    designator: str
    location: SchPoint
    electrical_type: SchPinElectricalType = (
        SchPinElectricalType.UNSPECIFIED
    )
    length_mm: float = 2.54
    rotation_deg: int = 0
    hidden: bool = False

    def validate(self) -> None:
        if not self.pin_id.strip():
            raise AltiumSchematicModelError(
                "Schematic pin_id cannot be empty."
            )
        if not self.designator.strip():
            raise AltiumSchematicModelError(
                f"Pin {self.pin_id!r} designator cannot be empty."
            )
        self.location.validate()
        if self.length_mm <= 0:
            raise AltiumSchematicModelError(
                f"Pin {self.pin_id!r} length must be greater than zero."
            )
        normalize_rotation(self.rotation_deg)


@dataclass(frozen=True)
class SchComponent:
    component_id: str
    reference: str
    value: str
    symbol_name: str
    location: SchPoint
    pins: tuple[SchPin, ...] = ()
    rotation_deg: int = 0
    mirrored: bool = False
    footprint: str | None = None
    description: str | None = None
    parameters: Mapping[str, str] | None = None

    def validate(self) -> None:
        if not self.component_id.strip():
            raise AltiumSchematicModelError(
                "Schematic component_id cannot be empty."
            )
        if not self.reference.strip():
            raise AltiumSchematicModelError(
                f"Component {self.component_id!r} reference cannot be empty."
            )
        if not self.symbol_name.strip():
            raise AltiumSchematicModelError(
                f"Component {self.component_id!r} symbol_name cannot be empty."
            )

        self.location.validate()
        normalize_rotation(self.rotation_deg)

        seen_pin_ids: set[str] = set()
        seen_designators: set[str] = set()
        for pin in self.pins:
            pin.validate()
            if pin.pin_id in seen_pin_ids:
                raise AltiumSchematicModelError(
                    f"Component {self.reference!r} has duplicate pin_id "
                    f"{pin.pin_id!r}."
                )
            seen_pin_ids.add(pin.pin_id)

            if pin.designator in seen_designators:
                raise AltiumSchematicModelError(
                    f"Component {self.reference!r} has duplicate pin "
                    f"designator {pin.designator!r}."
                )
            seen_designators.add(pin.designator)

        if self.parameters is not None:
            for name in self.parameters:
                if not str(name).strip():
                    raise AltiumSchematicModelError(
                        f"Component {self.reference!r} contains an empty "
                        "parameter name."
                    )
