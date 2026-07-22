from .altium_backend import AltiumBackend
from .backend import (
    BackendCapabilities,
    EDABackend,
    ExportRequest,
)
from .backend_registry import (
    BackendRegistry,
    BackendRegistryError,
)
from .export_result import ExportArtifact, ExportResult
from .kicad_backend import KiCadBackend
from .kicad_project_exporter import (
    KiCadProject,
    KiCadProjectExportError,
    KiCadProjectExporter,
    KiCadProjectMetadata,
    KiCadProjectValidator,
)
from .kicad_schematic_exporter import (
    KiCadSchematicExportError,
    KiCadSchematicExporter,
)


def create_default_backend_registry() -> BackendRegistry:
    """Create a registry containing all built-in backends."""

    return BackendRegistry(
        backends=(
            KiCadBackend(),
            AltiumBackend(),
        )
    )


_DEFAULT_BACKEND_REGISTRY = create_default_backend_registry()


def get_default_backend_registry() -> BackendRegistry:
    """Return the process-wide built-in backend registry."""

    return _DEFAULT_BACKEND_REGISTRY


def export_design(
    backend: str,
    request: ExportRequest,
    registry: BackendRegistry | None = None,
) -> ExportResult:
    """Export a design through a named EDA backend."""

    resolved_registry = (
        registry or get_default_backend_registry()
    )
    return resolved_registry.export(backend, request)


__all__ = [
    "AltiumBackend",
    "BackendCapabilities",
    "BackendRegistry",
    "BackendRegistryError",
    "EDABackend",
    "ExportArtifact",
    "ExportRequest",
    "ExportResult",
    "KiCadBackend",
    "KiCadProject",
    "KiCadProjectExportError",
    "KiCadProjectExporter",
    "KiCadProjectMetadata",
    "KiCadProjectValidator",
    "KiCadSchematicExportError",
    "KiCadSchematicExporter",
    "create_default_backend_registry",
    "export_design",
    "get_default_backend_registry",
]
