from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple


class SchematicModelError(Exception):
    """Raised when schematic data is invalid or inconsistent."""


@dataclass(frozen=True)
class SchematicPin:
    """One logical pin on a schematic component."""

    number: str
    name: str
    electrical_type: str = "passive"

    def validate(self) -> None:
        if not self.number.strip():
            raise SchematicModelError("Pin number cannot be empty.")
        if not self.name.strip():
            raise SchematicModelError("Pin name cannot be empty.")
        if not self.electrical_type.strip():
            raise SchematicModelError(
                "Pin electrical_type cannot be empty."
            )


@dataclass(frozen=True)
class SchematicComponent:
    """A component instance in a schematic design."""

    reference: str
    value: str
    symbol_name: str
    footprint_name: Optional[str] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    pins: Tuple[SchematicPin, ...] = ()
    fields: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.reference.strip():
            raise SchematicModelError(
                "Component reference cannot be empty."
            )
        if not self.value.strip():
            raise SchematicModelError(
                f"Component {self.reference} value cannot be empty."
            )
        if not self.symbol_name.strip():
            raise SchematicModelError(
                f"Component {self.reference} symbol_name cannot be empty."
            )

        pin_numbers: set[str] = set()
        pin_names: set[str] = set()

        for pin in self.pins:
            pin.validate()

            if pin.number in pin_numbers:
                raise SchematicModelError(
                    f"Component {self.reference} contains duplicate "
                    f"pin number {pin.number}."
                )
            pin_numbers.add(pin.number)

            normalized_name = pin.name.strip().lower()
            if normalized_name in pin_names:
                raise SchematicModelError(
                    f"Component {self.reference} contains duplicate "
                    f"pin name {pin.name}."
                )
            pin_names.add(normalized_name)

    def get_pin_by_name(self, name: str) -> SchematicPin:
        normalized = name.strip().lower()

        for pin in self.pins:
            if pin.name.strip().lower() == normalized:
                return pin

        raise KeyError(
            f"Component {self.reference} has no pin named '{name}'."
        )

    def get_pin_by_number(self, number: str) -> SchematicPin:
        normalized = number.strip()

        for pin in self.pins:
            if pin.number == normalized:
                return pin

        raise KeyError(
            f"Component {self.reference} has no pin number '{number}'."
        )


@dataclass(frozen=True)
class PinReference:
    """Reference to one component pin."""

    component_reference: str
    pin_number: str

    def validate(self) -> None:
        if not self.component_reference.strip():
            raise SchematicModelError(
                "PinReference component_reference cannot be empty."
            )
        if not self.pin_number.strip():
            raise SchematicModelError(
                "PinReference pin_number cannot be empty."
            )


@dataclass(frozen=True)
class SchematicNet:
    """Electrical net connecting one or more component pins."""

    name: str
    connections: Tuple[PinReference, ...]
    net_class: Optional[str] = None
    description: Optional[str] = None

    def validate(self) -> None:
        if not self.name.strip():
            raise SchematicModelError("Net name cannot be empty.")

        if len(self.connections) < 2:
            raise SchematicModelError(
                f"Net {self.name} must contain at least two connections."
            )

        seen: set[Tuple[str, str]] = set()

        for connection in self.connections:
            connection.validate()

            key = (
                connection.component_reference,
                connection.pin_number,
            )

            if key in seen:
                raise SchematicModelError(
                    f"Net {self.name} contains duplicate connection "
                    f"{connection.component_reference}."
                    f"{connection.pin_number}."
                )
            seen.add(key)


@dataclass
class SchematicDesign:
    """Technology-neutral schematic representation."""

    name: str
    components: List[SchematicComponent] = field(default_factory=list)
    nets: List[SchematicNet] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def add_component(
        self,
        component: SchematicComponent,
    ) -> None:
        component.validate()

        if any(
            existing.reference == component.reference
            for existing in self.components
        ):
            raise SchematicModelError(
                f"Duplicate component reference: {component.reference}"
            )

        self.components.append(component)

    def add_net(self, net: SchematicNet) -> None:
        net.validate()

        if any(existing.name == net.name for existing in self.nets):
            raise SchematicModelError(
                f"Duplicate net name: {net.name}"
            )

        self.nets.append(net)

    def get_component(
        self,
        reference: str,
    ) -> SchematicComponent:
        for component in self.components:
            if component.reference == reference:
                return component

        raise KeyError(f"Unknown component reference: {reference}")

    def get_net(self, name: str) -> SchematicNet:
        for net in self.nets:
            if net.name == name:
                return net

        raise KeyError(f"Unknown net: {name}")

    def validate(self) -> None:
        if not self.name.strip():
            raise SchematicModelError(
                "Schematic design name cannot be empty."
            )

        component_map: Dict[str, SchematicComponent] = {}

        for component in self.components:
            component.validate()

            if component.reference in component_map:
                raise SchematicModelError(
                    f"Duplicate component reference: "
                    f"{component.reference}"
                )

            component_map[component.reference] = component

        net_names: set[str] = set()
        connected_pins: Dict[Tuple[str, str], str] = {}

        for net in self.nets:
            net.validate()

            if net.name in net_names:
                raise SchematicModelError(
                    f"Duplicate net name: {net.name}"
                )
            net_names.add(net.name)

            for connection in net.connections:
                component = component_map.get(
                    connection.component_reference
                )

                if component is None:
                    raise SchematicModelError(
                        f"Net {net.name} references unknown component "
                        f"{connection.component_reference}."
                    )

                component.get_pin_by_number(connection.pin_number)

                key = (
                    connection.component_reference,
                    connection.pin_number,
                )

                previous_net = connected_pins.get(key)
                if previous_net is not None:
                    raise SchematicModelError(
                        f"Pin {connection.component_reference}."
                        f"{connection.pin_number} is connected to both "
                        f"{previous_net} and {net.name}."
                    )

                connected_pins[key] = net.name

    def iter_connections(
        self,
    ) -> Iterable[Tuple[str, PinReference]]:
        for net in self.nets:
            for connection in net.connections:
                yield net.name, connection

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "metadata": dict(self.metadata),
            "components": [
                {
                    "reference": component.reference,
                    "value": component.value,
                    "symbol_name": component.symbol_name,
                    "footprint_name": component.footprint_name,
                    "manufacturer": component.manufacturer,
                    "part_number": component.part_number,
                    "description": component.description,
                    "fields": dict(component.fields),
                    "pins": [
                        {
                            "number": pin.number,
                            "name": pin.name,
                            "electrical_type": pin.electrical_type,
                        }
                        for pin in component.pins
                    ],
                }
                for component in self.components
            ],
            "nets": [
                {
                    "name": net.name,
                    "net_class": net.net_class,
                    "description": net.description,
                    "connections": [
                        {
                            "component_reference": (
                                connection.component_reference
                            ),
                            "pin_number": connection.pin_number,
                        }
                        for connection in net.connections
                    ],
                }
                for net in self.nets
            ],
        }
