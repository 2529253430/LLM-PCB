from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class IRPin:
    """Technology-neutral logical component pin."""

    number: str
    name: str
    electrical_type: str = "passive"
    function: Optional[str] = None
    swap_group: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.number.strip():
            raise ValueError("IRPin number cannot be empty.")
        if not self.name.strip():
            raise ValueError("IRPin name cannot be empty.")
        if not self.electrical_type.strip():
            raise ValueError(
                "IRPin electrical_type cannot be empty."
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "number": self.number,
            "name": self.name,
            "electrical_type": self.electrical_type,
            "function": self.function,
            "swap_group": self.swap_group,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class IRComponent:
    """Technology-neutral component instance."""

    id: str
    reference: str
    value: str
    symbol_name: str
    pins: Tuple[IRPin, ...] = ()
    footprint_name: Optional[str] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("IRComponent id cannot be empty.")
        if not self.reference.strip():
            raise ValueError(
                "IRComponent reference cannot be empty."
            )
        if not self.value.strip():
            raise ValueError(
                f"IRComponent {self.reference} value cannot be empty."
            )
        if not self.symbol_name.strip():
            raise ValueError(
                f"IRComponent {self.reference} symbol_name cannot be empty."
            )

        pin_numbers: set[str] = set()
        for pin in self.pins:
            pin.validate()
            if pin.number in pin_numbers:
                raise ValueError(
                    f"IRComponent {self.reference} contains duplicate "
                    f"pin number {pin.number}."
                )
            pin_numbers.add(pin.number)

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "reference": self.reference,
            "value": self.value,
            "symbol_name": self.symbol_name,
            "footprint_name": self.footprint_name,
            "manufacturer": self.manufacturer,
            "part_number": self.part_number,
            "description": self.description,
            "parameters": dict(self.parameters),
            "metadata": dict(self.metadata),
            "pins": [pin.to_dict() for pin in self.pins],
        }
