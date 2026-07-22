from __future__ import annotations

from dataclasses import dataclass

from .primitives import AltiumSchematicModelError, SchPoint


@dataclass(frozen=True)
class SchWire:
    wire_id: str
    vertices: tuple[SchPoint, ...]
    net_id: str | None = None

    def validate(self) -> None:
        if not self.wire_id.strip():
            raise AltiumSchematicModelError(
                "Schematic wire_id cannot be empty."
            )
        if len(self.vertices) < 2:
            raise AltiumSchematicModelError(
                f"Wire {self.wire_id!r} must contain at least two vertices."
            )

        for point in self.vertices:
            point.validate()

        for start, end in zip(self.vertices, self.vertices[1:]):
            if start == end:
                raise AltiumSchematicModelError(
                    f"Wire {self.wire_id!r} contains a zero-length segment."
                )


@dataclass(frozen=True)
class SchJunction:
    junction_id: str
    location: SchPoint
    net_id: str | None = None

    def validate(self) -> None:
        if not self.junction_id.strip():
            raise AltiumSchematicModelError(
                "Schematic junction_id cannot be empty."
            )
        self.location.validate()
