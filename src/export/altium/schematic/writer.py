from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from .document import AltiumSchematicDocument


class AltiumSchematicPreviewWriter:
    """Write a deterministic diagnostic snapshot of the schematic model.

    This is not a native SchDoc writer. Its purpose in Phase 16A is to make
    the object model inspectable while the native serializer is developed.
    """

    def write(
        self,
        document: AltiumSchematicDocument,
        output_path: str | Path,
        *,
        overwrite: bool = True,
    ) -> Path:
        document.validate()

        destination = Path(output_path)
        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Schematic preview already exists: {destination}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(
                asdict(document),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return destination
