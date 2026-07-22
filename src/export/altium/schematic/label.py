from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .primitives import (
    AltiumSchematicModelError,
    SchPoint,
    normalize_rotation,
)


class SchPortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    UNSPECIFIED = "unspecified"


@dataclass(frozen=True)
class SchNetLabel:
    label_id: str
    text: str
    location: SchPoint
    net_id: str | None = None
    rotation_deg: int = 0

    def validate(self) -> None:
        if not self.label_id.strip():
            raise AltiumSchematicModelError(
                "Schematic label_id cannot be empty."
            )
        if not self.text.strip():
            raise AltiumSchematicModelError(
                f"Net label {self.label_id!r} text cannot be empty."
            )
        self.location.validate()
        normalize_rotation(self.rotation_deg)


@dataclass(frozen=True)
class SchPort:
    port_id: str
    name: str
    location: SchPoint
    direction: SchPortDirection = SchPortDirection.UNSPECIFIED
    net_id: str | None = None
    rotation_deg: int = 0

    def validate(self) -> None:
        if not self.port_id.strip():
            raise AltiumSchematicModelError(
                "Schematic port_id cannot be empty."
            )
        if not self.name.strip():
            raise AltiumSchematicModelError(
                f"Port {self.port_id!r} name cannot be empty."
            )
        self.location.validate()
        normalize_rotation(self.rotation_deg)


@dataclass(frozen=True)
class SchText:
    text_id: str
    text: str
    location: SchPoint
    rotation_deg: int = 0

    def validate(self) -> None:
        if not self.text_id.strip():
            raise AltiumSchematicModelError(
                "Schematic text_id cannot be empty."
            )
        if not self.text:
            raise AltiumSchematicModelError(
                f"Text object {self.text_id!r} cannot be empty."
            )
        self.location.validate()
        normalize_rotation(self.rotation_deg)
