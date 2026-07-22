from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class IRPoint:
    """Two-dimensional point expressed in millimetres."""

    x_mm: float
    y_mm: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "x_mm": float(self.x_mm),
            "y_mm": float(self.y_mm),
        }


@dataclass(frozen=True)
class IRSize:
    """Two-dimensional size expressed in millimetres."""

    width_mm: float
    height_mm: float

    def validate(self) -> None:
        if self.width_mm <= 0:
            raise ValueError("width_mm must be greater than zero.")
        if self.height_mm <= 0:
            raise ValueError("height_mm must be greater than zero.")

    def to_dict(self) -> Dict[str, float]:
        self.validate()
        return {
            "width_mm": float(self.width_mm),
            "height_mm": float(self.height_mm),
        }


@dataclass(frozen=True)
class IRSegment:
    """Line segment between two IR points."""

    start: IRPoint
    end: IRPoint

    @property
    def is_zero_length(self) -> bool:
        return self.start == self.end

    @property
    def is_orthogonal(self) -> bool:
        return (
            self.start.x_mm == self.end.x_mm
            or self.start.y_mm == self.end.y_mm
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
        }


@dataclass(frozen=True)
class IRPolygon:
    """Polygon defined by ordered points."""

    points: Tuple[IRPoint, ...]
    closed: bool = True

    def validate(self) -> None:
        minimum_points = 3 if self.closed else 2
        if len(self.points) < minimum_points:
            raise ValueError(
                f"Polygon requires at least {minimum_points} points."
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "closed": self.closed,
            "points": [point.to_dict() for point in self.points],
        }
