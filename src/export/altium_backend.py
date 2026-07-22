from __future__ import annotations

from .altium import (
    AltiumIntermediateWriteError,
    AltiumIntermediateWriter,
    AltiumProjectBuildError,
    AltiumProjectBuilder,
)
from .backend import BackendCapabilities, EDABackend, ExportRequest
from .export_result import ExportArtifact, ExportResult


class AltiumBackend(EDABackend):
    @property
    def name(self) -> str:
        return "altium"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            schematic=True,
            pcb=False,
            complete_project=False,
            native_format=False,
            validation=True,
            notes=(
                "Exports a validated Altium-oriented intermediate package.",
                "Native .PrjPcb, .SchDoc, and .PcbDoc are not emitted.",
            ),
        )

    def export(self, request: ExportRequest) -> ExportResult:
        missing = []
        if request.schematic is None:
            missing.append("schematic")
        if request.layout is None:
            missing.append("layout")
        if missing:
            return ExportResult(
                backend=self.name,
                success=False,
                project_name=request.project_name,
                errors=["Altium intermediate export requires: " + ", ".join(missing)],
                metadata={"capabilities": self.capabilities.to_dict()},
            )
        output_directory = request.output_root / request.project_name
        try:
            model = AltiumProjectBuilder().build(
                project_name=request.project_name,
                schematic=request.schematic,
                layout=request.layout,
                metadata=(
                    request.metadata
                    if isinstance(request.metadata, dict)
                    else {"source_metadata": request.metadata}
                ),
            )
            paths = AltiumIntermediateWriter().write(
                model,
                output_directory,
                overwrite=request.overwrite,
            )
        except (AltiumProjectBuildError, AltiumIntermediateWriteError, ValueError) as exc:
            return ExportResult(
                backend=self.name,
                success=False,
                project_name=request.project_name,
                output_directory=output_directory,
                errors=[str(exc)],
                metadata={"capabilities": self.capabilities.to_dict()},
            )
        artifacts = [
            ExportArtifact(role=role, path=path, media_type="application/json")
            for role, path in paths.items()
        ]
        return ExportResult(
            backend=self.name,
            success=True,
            project_name=request.project_name,
            output_directory=output_directory,
            artifacts=artifacts,
            warnings=[
                "The generated package is not a native Altium project and cannot yet be opened directly in Altium Designer."
            ],
            metadata={
                "capabilities": self.capabilities.to_dict(),
                "format": "llm-pcb-altium-intermediate",
                "format_version": "1.0",
                "component_count": len(model.components),
                "net_count": len(model.nets),
                "wire_count": len(model.wires),
            },
        )
