from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.export.kicad_schematic_exporter import (
    KiCadSchematicExporter,
)
from src.schematic.layout import SchematicLayout
from src.schematic.model import SchematicDesign


class KiCadProjectExportError(Exception):
    """Raised when a KiCad project cannot be generated safely."""


@dataclass(frozen=True)
class KiCadProject:
    """Paths and metadata for one generated KiCad project."""

    name: str
    directory: Path
    project_file: Path
    schematic_file: Path
    pcb_file: Path
    metadata_file: Path
    validation_file: Path

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "directory": str(self.directory),
            "project_file": str(self.project_file),
            "schematic_file": str(self.schematic_file),
            "pcb_file": str(self.pcb_file),
            "metadata_file": str(self.metadata_file),
            "validation_file": str(self.validation_file),
        }


@dataclass
class KiCadProjectMetadata:
    """Technology-neutral metadata stored beside the generated project."""

    topology: str
    generator: str = "LLM-PCB"
    generator_version: str = "0.11.1"
    requirements: Dict[str, Any] = field(default_factory=dict)
    selected_component: Dict[str, Any] = field(default_factory=dict)
    calculations: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(
        self,
        project_name: str,
        schematic: SchematicDesign,
        layout: SchematicLayout,
    ) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "project": {
                "name": project_name,
                "generated_by": self.generator,
                "generator_version": self.generator_version,
            },
            "design": {
                "topology": self.topology,
                "schematic_name": schematic.name,
                "component_count": len(schematic.components),
                "net_count": len(schematic.nets),
                "symbol_count": len(layout.symbols),
                "wire_count": len(layout.wires),
                "junction_count": len(layout.junctions),
                "label_count": len(layout.labels),
            },
            "requirements": dict(self.requirements),
            "selected_component": dict(
                self.selected_component
            ),
            "calculations": dict(self.calculations),
            "extra": dict(self.extra),
        }


class KiCadProjectExporter:
    """
    Generate a complete KiCad project directory.

    The PCB is currently supplied as an already-generated `.kicad_pcb`
    file. This deliberately decouples project packaging from the existing
    PCB exporter API. A later phase can inject the PCB exporter directly.
    """

    PROJECT_FILE_VERSION = 1

    def __init__(
        self,
        schematic_exporter: Optional[
            KiCadSchematicExporter
        ] = None,
    ) -> None:
        self.schematic_exporter = (
            schematic_exporter
            or KiCadSchematicExporter()
        )

    def export(
        self,
        project_name: str,
        schematic: SchematicDesign,
        layout: SchematicLayout,
        pcb_source_path: str | Path,
        output_root: str | Path,
        metadata: Optional[
            KiCadProjectMetadata
        ] = None,
        overwrite: bool = True,
    ) -> KiCadProject:
        schematic.validate()
        layout.validate(schematic)

        safe_name = self._safe_project_name(project_name)
        source_pcb = Path(pcb_source_path)

        if not source_pcb.exists():
            raise KiCadProjectExportError(
                f"PCB source file does not exist: {source_pcb}"
            )

        if source_pcb.suffix.lower() != ".kicad_pcb":
            raise KiCadProjectExportError(
                "pcb_source_path must use the .kicad_pcb extension."
            )

        output_directory = Path(output_root) / safe_name

        if output_directory.exists():
            if not overwrite:
                raise KiCadProjectExportError(
                    f"Project directory already exists: "
                    f"{output_directory}"
                )

            if not output_directory.is_dir():
                raise KiCadProjectExportError(
                    f"Output path exists but is not a directory: "
                    f"{output_directory}"
                )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        project_file = (
            output_directory
            / f"{safe_name}.kicad_pro"
        )
        schematic_file = (
            output_directory
            / f"{safe_name}.kicad_sch"
        )
        pcb_file = (
            output_directory
            / f"{safe_name}.kicad_pcb"
        )
        metadata_file = (
            output_directory
            / "metadata.json"
        )
        validation_file = (
            output_directory
            / "validation.json"
        )

        self.schematic_exporter.export(
            design=schematic,
            layout=layout,
            output_path=schematic_file,
        )

        self._copy_pcb(
            source=source_pcb,
            destination=pcb_file,
        )

        self._write_project_file(project_file)

        resolved_metadata = (
            metadata
            or KiCadProjectMetadata(
                topology=layout.metadata.get(
                    "topology",
                    "unknown",
                )
            )
        )

        metadata_payload = resolved_metadata.to_dict(
            project_name=safe_name,
            schematic=schematic,
            layout=layout,
        )

        self._write_json(
            metadata_file,
            metadata_payload,
        )

        project = KiCadProject(
            name=safe_name,
            directory=output_directory,
            project_file=project_file,
            schematic_file=schematic_file,
            pcb_file=pcb_file,
            metadata_file=metadata_file,
            validation_file=validation_file,
        )

        validation_payload = (
            KiCadProjectValidator().validate(
                project=project,
                schematic=schematic,
                layout=layout,
            )
        )

        self._write_json(
            validation_file,
            validation_payload,
        )

        if not validation_payload["valid"]:
            errors = "; ".join(
                validation_payload["errors"]
            )
            raise KiCadProjectExportError(
                f"Generated KiCad project failed validation: "
                f"{errors}"
            )

        return project

    def _write_project_file(
        self,
        path: Path,
    ) -> None:
        """
        KiCad `.kicad_pro` files are JSON settings files.

        Only stable, minimal settings are emitted here. KiCad may add more
        settings when the project is first saved in the GUI.
        """
        payload = {
            "board": {},
            "boards": [],
            "cvpcb": {},
            "erc": {},
            "libraries": {},
            "meta": {
                "filename": path.name,
                "version": self.PROJECT_FILE_VERSION,
            },
            "net_settings": {
                "classes": [],
                "meta": {
                    "version": 3,
                },
            },
            "pcbnew": {},
            "schematic": {},
            "sheets": [],
            "text_variables": {},
        }

        self._write_json(path, payload)

    @staticmethod
    def _copy_pcb(
        source: Path,
        destination: Path,
    ) -> None:
        try:
            if source.resolve() == destination.resolve():
                return
        except FileNotFoundError:
            pass

        shutil.copy2(source, destination)

    @staticmethod
    def _write_json(
        path: Path,
        payload: Mapping[str, Any],
    ) -> None:
        path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _safe_project_name(name: str) -> str:
        cleaned = name.strip()

        if not cleaned:
            raise KiCadProjectExportError(
                "project_name cannot be empty."
            )

        safe = "".join(
            character
            if character.isalnum()
            or character in {"_", "-"}
            else "_"
            for character in cleaned
        )

        safe = safe.strip("_")

        if not safe:
            raise KiCadProjectExportError(
                "project_name contains no usable characters."
            )

        return safe


class KiCadProjectValidator:
    """Validate the generated project before Altium import."""

    REQUIRED_PROJECT_KEYS = {
        "board",
        "erc",
        "libraries",
        "meta",
        "net_settings",
        "pcbnew",
        "schematic",
    }

    def validate(
        self,
        project: KiCadProject,
        schematic: SchematicDesign,
        layout: SchematicLayout,
    ) -> Dict[str, Any]:
        errors = []
        warnings = []

        required_files = {
            "project": project.project_file,
            "schematic": project.schematic_file,
            "pcb": project.pcb_file,
            "metadata": project.metadata_file,
        }

        file_status: Dict[str, Dict[str, Any]] = {}

        for role, path in required_files.items():
            exists = path.exists()
            nonempty = exists and path.stat().st_size > 0

            file_status[role] = {
                "path": str(path),
                "exists": exists,
                "nonempty": nonempty,
                "size_bytes": (
                    path.stat().st_size
                    if exists
                    else 0
                ),
            }

            if not exists:
                errors.append(
                    f"Missing {role} file: {path.name}"
                )
            elif not nonempty:
                errors.append(
                    f"Empty {role} file: {path.name}"
                )

        if project.project_file.exists():
            self._validate_project_json(
                project.project_file,
                errors,
            )

        if project.schematic_file.exists():
            self._validate_schematic_text(
                project.schematic_file,
                schematic,
                layout,
                errors,
                warnings,
            )

        if project.pcb_file.exists():
            self._validate_pcb_text(
                project.pcb_file,
                errors,
                warnings,
            )

        same_stem = (
            project.project_file.stem
            == project.schematic_file.stem
            == project.pcb_file.stem
            == project.name
        )

        if not same_stem:
            errors.append(
                "Project, schematic, and PCB filenames "
                "must share the same stem."
            )

        return {
            "schema_version": "1.0",
            "project_name": project.name,
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "files": file_status,
            "design_counts": {
                "components": len(
                    schematic.components
                ),
                "nets": len(schematic.nets),
                "symbols": len(layout.symbols),
                "wires": len(layout.wires),
                "junctions": len(
                    layout.junctions
                ),
                "labels": len(layout.labels),
            },
        }

    def _validate_project_json(
        self,
        path: Path,
        errors: list[str],
    ) -> None:
        try:
            payload = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            errors.append(
                f"Invalid .kicad_pro JSON: {exc}"
            )
            return

        if not isinstance(payload, dict):
            errors.append(
                ".kicad_pro root must be a JSON object."
            )
            return

        missing = (
            self.REQUIRED_PROJECT_KEYS
            - set(payload)
        )

        if missing:
            errors.append(
                "Missing .kicad_pro keys: "
                + ", ".join(sorted(missing))
            )

    @staticmethod
    def _validate_schematic_text(
        path: Path,
        schematic: SchematicDesign,
        layout: SchematicLayout,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        text = path.read_text(
            encoding="utf-8"
        )

        if not text.startswith("(kicad_sch"):
            errors.append(
                "Schematic is not a modern "
                ".kicad_sch file."
            )

        missing_references = [
            component.reference
            for component in schematic.components
            if (
                f'(reference '
                f'"{component.reference}")'
            )
            not in text
        ]

        if missing_references:
            errors.append(
                "Schematic is missing references: "
                + ", ".join(missing_references)
            )

        wire_count = text.count("(wire")

        if wire_count != len(layout.wires):
            errors.append(
                "Schematic wire count does not "
                "match SchematicLayout."
            )

        if "(sheet_instances" not in text:
            warnings.append(
                "Schematic has no sheet_instances block."
            )

    @staticmethod
    def _validate_pcb_text(
        path: Path,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            errors.append(
                "PCB file is not UTF-8 text."
            )
            return

        if not text.lstrip().startswith(
            "(kicad_pcb"
        ):
            errors.append(
                "PCB source is not a modern "
                ".kicad_pcb file."
            )

        if "(footprint" not in text:
            warnings.append(
                "PCB file contains no footprint blocks."
            )

        if "(segment" not in text:
            warnings.append(
                "PCB file contains no routed segments."
            )
