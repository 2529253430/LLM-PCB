from __future__ import annotations

from typing import Any, Dict
from src.design_ir import (
    SchematicDesignAdapter, SchematicDesignAdapterError,
    UniversalProjectIR, UniversalProjectValidator,
)
from .altium import (
    AltiumIntermediateWriteError, AltiumIntermediateWriter,
    AltiumPrjPcbWriter, AltiumProjectBuildError, AltiumProjectBuilder,
    AltiumProjectFile, AltiumProjectFileError,
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
            schematic=True, pcb=False, complete_project=False,
            native_format=True, validation=True,
            notes=(
                "Consumes UniversalProjectIR as its canonical input.",
                "Emits a native ASCII .PrjPcb project shell.",
                "Legacy schematic/layout input is converted through the IR adapter.",
                "Native .SchDoc and .PcbDoc documents are not emitted yet.",
            ),
        )

    def export(self, request: ExportRequest) -> ExportResult:
        try:
            request.validate_common()
        except ValueError as exc:
            return self._failure(request=request, errors=[str(exc)])
        output_directory = request.output_root / request.project_name
        try:
            project_ir, input_mode = self._resolve_project_ir(request)
            validation_report = UniversalProjectValidator().require_valid(project_ir)
            model = AltiumProjectBuilder().build_from_ir(
                project_ir, project_name=request.project_name,
                metadata=self._metadata_dict(request.metadata),
            )
            intermediate_paths = AltiumIntermediateWriter().write(
                model, output_directory, overwrite=request.overwrite,
            )
            project_file = AltiumProjectFile(
                project_name=request.project_name,
                documents=(),
                parameters={
                    "LLMPCBProjectId": project_ir.project_id,
                    "LLMPCBIRSchema": project_ir.SCHEMA_NAME,
                    "LLMPCBIRVersion": project_ir.schema_version,
                    "ProjectName": request.project_name,
                },
            )
            prjpcb_path = AltiumPrjPcbWriter().write(
                project_file, output_directory, overwrite=request.overwrite,
            )
        except (
            SchematicDesignAdapterError, AltiumProjectBuildError,
            AltiumIntermediateWriteError, AltiumProjectFileError,
            ValueError, KeyError,
        ) as exc:
            return self._failure(
                request=request, output_directory=output_directory,
                errors=[str(exc)],
            )
        artifacts = [
            ExportArtifact(role=role, path=path, media_type="application/json")
            for role, path in intermediate_paths.items()
        ]
        artifacts.insert(0, ExportArtifact(
            role="altium_project", path=prjpcb_path, media_type="text/plain",
        ))
        return ExportResult(
            backend=self.name, success=True, project_name=request.project_name,
            output_directory=output_directory, artifacts=artifacts,
            warnings=[
                "The .PrjPcb file is a native Altium project shell.",
                "No SchDoc or PcbDoc is registered yet; schematic generation is introduced in Phase 16.",
                "The JSON files remain diagnostic intermediate artifacts.",
            ],
            metadata={
                "capabilities": self.capabilities.to_dict(),
                "format": "altium-prjpcb-plus-intermediate", "format_version": "1.0",
                "input_mode": input_mode, "ir_schema": project_ir.SCHEMA_NAME,
                "ir_schema_version": project_ir.schema_version,
                "ir_validation": validation_report.to_dict(),
                "component_count": len(model.components), "net_count": len(model.nets),
                "wire_count": len(model.wires), "native_project_document_count": 0,
            },
        )

    def _resolve_project_ir(self, request: ExportRequest) -> tuple[UniversalProjectIR, str]:
        if request.project_ir is not None:
            return request.project_ir, "universal_project_ir"
        missing = []
        if request.schematic is None:
            missing.append("schematic")
        if request.layout is None:
            missing.append("layout")
        if missing:
            raise ValueError(
                "Altium export requires project_ir or legacy inputs: " + ", ".join(missing)
            )
        return SchematicDesignAdapter().build(
            request.schematic, request.layout,
            project_name=request.project_name,
            metadata=self._metadata_dict(request.metadata),
        ), "legacy_adapter"

    def _failure(self, *, request: ExportRequest, errors: list[str], output_directory=None) -> ExportResult:
        return ExportResult(
            backend=self.name, success=False, project_name=request.project_name,
            output_directory=output_directory, errors=errors,
            metadata={"capabilities": self.capabilities.to_dict()},
        )

    @staticmethod
    def _metadata_dict(metadata: Any) -> Dict[str, Any]:
        if metadata is None:
            return {}
        if isinstance(metadata, dict):
            return dict(metadata)
        return {"source_metadata": metadata}
