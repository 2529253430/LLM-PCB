from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from .backend import (
    BackendCapabilities,
    EDABackend,
    ExportRequest,
)
from .export_result import ExportArtifact, ExportResult
from .kicad_project_exporter import (
    KiCadProjectExportError,
    KiCadProjectExporter,
    KiCadProjectMetadata,
)


class KiCadBackend(EDABackend):
    """Adapter exposing KiCadProjectExporter through the common API."""

    def __init__(
        self,
        project_exporter: KiCadProjectExporter | None = None,
    ) -> None:
        self.project_exporter = (
            project_exporter or KiCadProjectExporter()
        )

    @property
    def name(self) -> str:
        return "kicad"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            schematic=True,
            pcb=True,
            complete_project=True,
            native_format=True,
            validation=True,
            notes=(
                "PCB input is currently supplied as an existing "
                ".kicad_pcb file.",
            ),
        )

    def export(self, request: ExportRequest) -> ExportResult:
        missing = []
        if request.schematic is None:
            missing.append("schematic")
        if request.layout is None:
            missing.append("layout")
        if request.pcb_source_path is None:
            missing.append("pcb_source_path")

        if missing:
            return ExportResult(
                backend=self.name,
                success=False,
                project_name=request.project_name,
                errors=[
                    "KiCad backend requires: "
                    + ", ".join(missing)
                ],
                metadata={
                    "capabilities": self.capabilities.to_dict(),
                },
            )

        try:
            project = self.project_exporter.export(
                project_name=request.project_name,
                schematic=request.schematic,
                layout=request.layout,
                pcb_source_path=request.pcb_source_path,
                output_root=request.output_root,
                metadata=self._resolve_metadata(
                    request.metadata,
                    request.layout.metadata,
                ),
                overwrite=request.overwrite,
            )
        except (
            KiCadProjectExportError,
            OSError,
            ValueError,
        ) as exc:
            return ExportResult(
                backend=self.name,
                success=False,
                project_name=request.project_name,
                errors=[str(exc)],
                metadata={
                    "capabilities": self.capabilities.to_dict(),
                },
            )

        artifacts = [
            ExportArtifact(
                "project",
                project.project_file,
                "application/json",
            ),
            ExportArtifact(
                "schematic",
                project.schematic_file,
                "application/x-kicad-schematic",
            ),
            ExportArtifact(
                "pcb",
                project.pcb_file,
                "application/x-kicad-pcb",
            ),
            ExportArtifact(
                "metadata",
                project.metadata_file,
                "application/json",
            ),
            ExportArtifact(
                "validation",
                project.validation_file,
                "application/json",
            ),
        ]

        return ExportResult(
            backend=self.name,
            success=True,
            project_name=project.name,
            output_directory=project.directory,
            artifacts=artifacts,
            metadata={
                "capabilities": self.capabilities.to_dict(),
                "project": project.to_dict(),
            },
        )

    @staticmethod
    def _resolve_metadata(
        value: Any,
        layout_metadata: Mapping[str, Any],
    ) -> KiCadProjectMetadata:
        if isinstance(value, KiCadProjectMetadata):
            return value

        if value is None:
            return KiCadProjectMetadata(
                topology=str(
                    layout_metadata.get("topology", "unknown")
                )
            )

        if is_dataclass(value):
            value = asdict(value)

        if not isinstance(value, Mapping):
            raise ValueError(
                "KiCad metadata must be KiCadProjectMetadata, "
                "a mapping, a dataclass, or None."
            )

        known = {
            "topology",
            "generator",
            "generator_version",
            "requirements",
            "selected_component",
            "calculations",
            "extra",
        }
        extra = dict(value.get("extra", {}))
        for key, item in value.items():
            if key not in known:
                extra[str(key)] = item

        return KiCadProjectMetadata(
            topology=str(
                value.get(
                    "topology",
                    layout_metadata.get("topology", "unknown"),
                )
            ),
            generator=str(value.get("generator", "LLM-PCB")),
            generator_version=str(
                value.get("generator_version", "0.12.0")
            ),
            requirements=dict(value.get("requirements", {})),
            selected_component=dict(
                value.get("selected_component", {})
            ),
            calculations=dict(value.get("calculations", {})),
            extra=extra,
        )
