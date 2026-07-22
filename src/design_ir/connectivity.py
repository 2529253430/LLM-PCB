from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class IRPinRef:
    """Reference to one logical component pin."""

    component_id: str
    pin_number: str

    def validate(self) -> None:
        if not self.component_id.strip():
            raise ValueError(
                "IRPinRef component_id cannot be empty."
            )
        if not self.pin_number.strip():
            raise ValueError(
                "IRPinRef pin_number cannot be empty."
            )

    def to_dict(self) -> Dict[str, str]:
        self.validate()
        return {
            "component_id": self.component_id,
            "pin_number": self.pin_number,
        }


@dataclass(frozen=True)
class IRNet:
    """Technology-neutral logical electrical net."""

    id: str
    name: str
    connections: Tuple[IRPinRef, ...]
    net_class: Optional[str] = None
    description: Optional[str] = None
    constraints: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("IRNet id cannot be empty.")
        if not self.name.strip():
            raise ValueError("IRNet name cannot be empty.")
        if len(self.connections) < 2:
            raise ValueError(
                f"IRNet {self.name} must contain at least two "
                "connections."
            )

        seen: set[tuple[str, str]] = set()
        for connection in self.connections:
            connection.validate()
            key = (
                connection.component_id,
                connection.pin_number,
            )
            if key in seen:
                raise ValueError(
                    f"IRNet {self.name} contains duplicate connection "
                    f"{connection.component_id}.{connection.pin_number}."
                )
            seen.add(key)

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "name": self.name,
            "net_class": self.net_class,
            "description": self.description,
            "constraints": dict(self.constraints),
            "metadata": dict(self.metadata),
            "connections": [
                connection.to_dict()
                for connection in self.connections
            ],
        }
