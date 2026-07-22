from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .model import AltiumProjectModel


class AltiumIntermediateWriteError(Exception):
    """Raised when an Altium intermediate package cannot be written."""


class AltiumIntermediateWriter:
    MODEL_FILENAME = "altium_project_model.json"
    MANIFEST_FILENAME = "manifest.json"

    def write(
        self,
        model: AltiumProjectModel,
        output_directory: str | Path,
        *,
        overwrite: bool = True,
    ) -> Dict[str, Path]:
        model.validate()
        destination = Path(output_directory)
        if destination.exists() and not destination.is_dir():
            raise AltiumIntermediateWriteError(f"Output path is not a directory: {destination}")
        destination.mkdir(parents=True, exist_ok=True)
        model_path = destination / self.MODEL_FILENAME
        manifest_path = destination / self.MANIFEST_FILENAME
        for path in (model_path, manifest_path):
            if path.exists() and not overwrite:
                raise AltiumIntermediateWriteError(f"Output file already exists: {path}")
        self._write_json(model_path, model.to_dict())
        self._write_json(
            manifest_path,
            {
                "format": "llm-pcb-altium-intermediate",
                "format_version": "1.0",
                "project_name": model.project_name,
                "native_altium": False,
                "artifacts": {"project_model": self.MODEL_FILENAME},
                "planned_native_artifacts": [
                    f"{model.project_name}.PrjPcb",
                    f"{model.project_name}.SchDoc",
                    f"{model.project_name}.PcbDoc",
                ],
                "notes": [
                    "This package is an Altium-oriented intermediate representation.",
                    "It is not directly openable by Altium Designer yet.",
                ],
            },
        )
        return {"altium_model": model_path, "manifest": manifest_path}

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        try:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise AltiumIntermediateWriteError(f"Failed to write {path}: {exc}") from exc
