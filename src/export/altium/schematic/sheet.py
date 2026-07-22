from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .primitives import AltiumSchematicModelError, SchSize


class SchSheetOrientation(str, Enum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


@dataclass(frozen=True)
class SchSheet:
    name: str
    size: SchSize = SchSize(297.0, 210.0)
    orientation: SchSheetOrientation = SchSheetOrientation.LANDSCAPE
    grid_mm: float = 2.54
    title: str = ""
    document_number: str = ""
    revision: str = ""
    company: str = ""
    author: str = ""

    def validate(self) -> None:
        if not self.name.strip():
            raise AltiumSchematicModelError(
                "Schematic sheet name cannot be empty."
            )
        self.size.validate()
        if self.grid_mm <= 0:
            raise AltiumSchematicModelError(
                "Schematic sheet grid_mm must be greater than zero."
            )
