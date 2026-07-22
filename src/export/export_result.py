from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass(frozen=True)
class ExportArtifact:
    """One file or directory produced by an EDA backend."""

    role: str
    path: Path
    media_type: str = "application/octet-stream"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "path": str(self.path),
            "media_type": self.media_type,
            "exists": self.exists,
            "metadata": dict(self.metadata),
        }


@dataclass
class ExportResult:
    """Technology-neutral result returned by every EDA backend."""

    backend: str
    success: bool
    project_name: str
    output_directory: Optional[Path] = None
    artifacts: List[ExportArtifact] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def files(self) -> List[Path]:
        return [
            artifact.path
            for artifact in self.artifacts
            if artifact.path.is_file()
        ]

    def add_artifacts(
        self,
        artifacts: Iterable[ExportArtifact],
    ) -> None:
        self.artifacts.extend(artifacts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "success": self.success,
            "project_name": self.project_name,
            "output_directory": (
                str(self.output_directory)
                if self.output_directory is not None
                else None
            ),
            "artifacts": [
                artifact.to_dict()
                for artifact in self.artifacts
            ],
            "files": [str(path) for path in self.files],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }
