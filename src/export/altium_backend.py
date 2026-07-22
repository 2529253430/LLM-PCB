from __future__ import annotations

from .backend import (
    BackendCapabilities,
    EDABackend,
    ExportRequest,
)
from .export_result import ExportResult


class AltiumBackend(EDABackend):
    """
    Capability placeholder for future native Altium export.

    The backend deliberately does not create fake SchDoc or PcbDoc files.
    Those formats require a separately validated implementation.
    """

    @property
    def name(self) -> str:
        return "altium"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            schematic=False,
            pcb=False,
            complete_project=False,
            native_format=False,
            validation=False,
            notes=(
                "Native Altium export is planned but not implemented.",
                "No placeholder .SchDoc or .PcbDoc files are emitted.",
            ),
        )

    def export(self, request: ExportRequest) -> ExportResult:
        return ExportResult(
            backend=self.name,
            success=False,
            project_name=request.project_name,
            errors=[
                "Altium backend is registered but native export is "
                "not implemented yet."
            ],
            metadata={
                "capabilities": self.capabilities.to_dict(),
                "planned_artifacts": [
                    ".PrjPcb",
                    ".SchDoc",
                    ".PcbDoc",
                ],
            },
        )
