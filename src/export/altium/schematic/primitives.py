from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


class AltiumSchematicModelError(ValueError):
    """Raised when the Altium schematic object model is invalid."""


@dataclass(frozen=True, order=True)
class SchPoint:
    """A point in Altium schematic model space.

    Phase 16A stores positions in millimetres. The native writer introduced
    later is responsible for converting them to Altium internal coordinates.
    """

    x_mm: float
    y_mm: float

    def validate(self) -> None:
        if not isfinite(self.x_mm) or not isfinite(self.y_mm):
            raise AltiumSchematicModelError(
                "Schematic point coordinates must be finite."
            )


@dataclass(frozen=True)
class SchSize:
    width_mm: float
    height_mm: float

    def validate(self) -> None:
        if not isfinite(self.width_mm) or not isfinite(self.height_mm):
            raise AltiumSchematicModelError(
                "Schematic size values must be finite."
            )
        if self.width_mm <= 0 or self.height_mm <= 0:
            raise AltiumSchematicModelError(
                "Schematic width and height must be greater than zero."
            )


@dataclass(frozen=True)
class SchRectangle:
    origin: SchPoint
    size: SchSize

    def validate(self) -> None:
        self.origin.validate()
        self.size.validate()


def normalize_rotation(rotation_deg: int) -> int:
    normalized = rotation_deg % 360
    if normalized not in {0, 90, 180, 270}:
        raise AltiumSchematicModelError(
            "Schematic rotation must be one of 0, 90, 180, or 270 degrees."
        )
    return normalized
