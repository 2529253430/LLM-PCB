from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.schematic.layout import SchematicLayout
from src.schematic.model import SchematicDesign

from .export_result import ExportResult


@dataclass(frozen=True)
class BackendCapabilities:
    """Feature declaration for one EDA export backend."""

    schematic: bool
    pcb: bool
    complete_project: bool
    native_format: bool
    validation: bool
    notes: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schematic": self.schematic,
            "pcb": self.pcb,
            "complete_project": self.complete_project,
            "native_format": self.native_format,
            "validation": self.validation,
            "notes": list(self.notes),
        }


@dataclass
class ExportRequest:
    """Technology-neutral input passed to an EDA backend."""

    project_name: str
    output_root: Path
    schematic: Optional[SchematicDesign] = None
    layout: Optional[SchematicLayout] = None
    pcb_source_path: Optional[Path] = None
    metadata: Any = None
    overwrite: bool = True
    options: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        project_name: str,
        output_root: str | Path,
        schematic: Optional[SchematicDesign] = None,
        layout: Optional[SchematicLayout] = None,
        pcb_source_path: Optional[str | Path] = None,
        metadata: Any = None,
        overwrite: bool = True,
        options: Optional[Mapping[str, Any]] = None,
    ) -> "ExportRequest":
        return cls(
            project_name=project_name,
            output_root=Path(output_root),
            schematic=schematic,
            layout=layout,
            pcb_source_path=(
                Path(pcb_source_path)
                if pcb_source_path is not None
                else None
            ),
            metadata=metadata,
            overwrite=overwrite,
            options=dict(options or {}),
        )

    def validate_common(self) -> None:
        if not self.project_name.strip():
            raise ValueError("project_name cannot be empty.")


class EDABackend(ABC):
    """Base interface implemented by all EDA exporters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable registry name for the backend."""

    @property
    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """Features currently supported by the backend."""

    @abstractmethod
    def export(self, request: ExportRequest) -> ExportResult:
        """Export one design request."""
