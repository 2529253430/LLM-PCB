from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class IRConstraintSet:
    """Project-level technology-neutral design constraints."""

    minimum_track_width_mm: Optional[float] = None
    preferred_track_width_mm: Optional[float] = None
    minimum_clearance_mm: Optional[float] = None
    via_diameter_mm: Optional[float] = None
    via_drill_mm: Optional[float] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        numeric_values = {
            "minimum_track_width_mm": self.minimum_track_width_mm,
            "preferred_track_width_mm": (
                self.preferred_track_width_mm
            ),
            "minimum_clearance_mm": self.minimum_clearance_mm,
            "via_diameter_mm": self.via_diameter_mm,
            "via_drill_mm": self.via_drill_mm,
        }
        for name, value in numeric_values.items():
            if value is not None and value <= 0:
                raise ValueError(
                    f"{name} must be greater than zero."
                )

        if (
            self.minimum_track_width_mm is not None
            and self.preferred_track_width_mm is not None
            and self.minimum_track_width_mm
            > self.preferred_track_width_mm
        ):
            raise ValueError(
                "minimum_track_width_mm cannot exceed "
                "preferred_track_width_mm."
            )

        if (
            self.via_diameter_mm is not None
            and self.via_drill_mm is not None
            and self.via_drill_mm >= self.via_diameter_mm
        ):
            raise ValueError(
                "via_drill_mm must be smaller than "
                "via_diameter_mm."
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "minimum_track_width_mm": (
                self.minimum_track_width_mm
            ),
            "preferred_track_width_mm": (
                self.preferred_track_width_mm
            ),
            "minimum_clearance_mm": self.minimum_clearance_mm,
            "via_diameter_mm": self.via_diameter_mm,
            "via_drill_mm": self.via_drill_mm,
            "metadata": dict(self.metadata),
        }
