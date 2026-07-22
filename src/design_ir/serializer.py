from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .project import UniversalProjectIR
from .validator import UniversalProjectValidator


class UniversalProjectIRSerializationError(Exception):
    """Raised when universal IR serialization fails."""


class UniversalProjectIRSerializer:
    """Write deterministic universal-project JSON and validation data."""

    PROJECT_FILENAME = "project_ir.json"
    VALIDATION_FILENAME = "project_ir_validation.json"

    def write(
        self,
        project: UniversalProjectIR,
        output_directory: str | Path,
        *,
        overwrite: bool = True,
    ) -> Dict[str, Path]:
        validator = UniversalProjectValidator()
        report = validator.require_valid(project)

        destination = Path(output_directory)
        if destination.exists() and not destination.is_dir():
            raise UniversalProjectIRSerializationError(
                f"Output path is not a directory: {destination}"
            )
        destination.mkdir(parents=True, exist_ok=True)

        project_path = destination / self.PROJECT_FILENAME
        validation_path = destination / self.VALIDATION_FILENAME

        for path in (project_path, validation_path):
            if path.exists() and not overwrite:
                raise UniversalProjectIRSerializationError(
                    f"Output file already exists: {path}"
                )

        self._write_json(project_path, project.to_dict())
        self._write_json(validation_path, report.to_dict())

        return {
            "project_ir": project_path,
            "validation": validation_path,
        }

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        try:
            text = json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                separators=(",", ": "),
            )
            path.write_text(text + "\n", encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            raise UniversalProjectIRSerializationError(
                f"Failed to write {path}: {exc}"
            ) from exc
