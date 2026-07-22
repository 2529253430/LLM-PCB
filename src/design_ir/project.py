from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from .component import IRComponent
from .connectivity import IRNet
from .constraints import IRConstraintSet
from .schematic import IRSchematic


@dataclass
class UniversalProjectIR:
    """Root object for the technology-neutral LLM-PCB project IR."""

    project_id: str
    project_name: str
    schematic: IRSchematic
    components: Tuple[IRComponent, ...]
    nets: Tuple[IRNet, ...]
    constraints: IRConstraintSet = field(
        default_factory=IRConstraintSet
    )
    board: Optional[Any] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"

    SCHEMA_NAME = "llm-pcb.universal-project-ir"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.SCHEMA_NAME,
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "metadata": dict(self.metadata),
            "components": [
                component.to_dict()
                for component in self.components
            ],
            "nets": [net.to_dict() for net in self.nets],
            "constraints": self.constraints.to_dict(),
            "schematic": self.schematic.to_dict(),
            "board": (
                self.board.to_dict()
                if self.board is not None
                and hasattr(self.board, "to_dict")
                else self.board
            ),
        }
