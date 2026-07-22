from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .component import SchComponent
from .label import SchNetLabel, SchPort, SchText
from .primitives import AltiumSchematicModelError
from .sheet import SchSheet
from .wire import SchJunction, SchWire


@dataclass(frozen=True)
class AltiumSchematicDocument:
    """Backend-level model of one Altium schematic document.

    It is deliberately independent from the binary SchDoc serialization.
    """

    document_id: str
    name: str
    sheet: SchSheet
    components: tuple[SchComponent, ...] = ()
    wires: tuple[SchWire, ...] = ()
    labels: tuple[SchNetLabel, ...] = ()
    ports: tuple[SchPort, ...] = ()
    junctions: tuple[SchJunction, ...] = ()
    texts: tuple[SchText, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.document_id.strip():
            raise AltiumSchematicModelError(
                "Schematic document_id cannot be empty."
            )
        if not self.name.strip():
            raise AltiumSchematicModelError(
                "Schematic document name cannot be empty."
            )
        self.sheet.validate()

        self._validate_unique(
            "component",
            (item.component_id for item in self.components),
        )
        self._validate_unique(
            "reference",
            (item.reference for item in self.components),
        )
        self._validate_unique(
            "wire",
            (item.wire_id for item in self.wires),
        )
        self._validate_unique(
            "label",
            (item.label_id for item in self.labels),
        )
        self._validate_unique(
            "port",
            (item.port_id for item in self.ports),
        )
        self._validate_unique(
            "junction",
            (item.junction_id for item in self.junctions),
        )
        self._validate_unique(
            "text",
            (item.text_id for item in self.texts),
        )

        for collection in (
            self.components,
            self.wires,
            self.labels,
            self.ports,
            self.junctions,
            self.texts,
        ):
            for item in collection:
                item.validate()

    @staticmethod
    def _validate_unique(
        object_type: str,
        values,
    ) -> None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                raise AltiumSchematicModelError(
                    f"Duplicate schematic {object_type}: {value!r}."
                )
            seen.add(value)

    @property
    def object_count(self) -> int:
        return (
            len(self.components)
            + len(self.wires)
            + len(self.labels)
            + len(self.ports)
            + len(self.junctions)
            + len(self.texts)
        )
