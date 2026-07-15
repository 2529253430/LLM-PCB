from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Rectangle:
    """
    一个轴对齐矩形（Axis-Aligned Bounding Box，AABB）。

    单位：mm
    """

    left: float
    right: float
    bottom: float
    top: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    def contains_point(
        self,
        x: float,
        y: float,
    ) -> bool:
        """
        判断点是否位于矩形内部（含边界）。
        """

        return (
            self.left <= x <= self.right
            and self.bottom <= y <= self.top
        )

    def intersects(
        self,
        other: "Rectangle",
    ) -> bool:
        """
        判断两个矩形是否相交。
        """

        separated = (
            self.right <= other.left
            or other.right <= self.left
            or self.top <= other.bottom
            or other.top <= self.bottom
        )

        return not separated

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "bottom": self.bottom,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class PCBObstacle:
    """
    PCB上的障碍物。

    当前默认一个元件对应一个矩形障碍物。
    """

    reference: str
    obstacle_type: str
    rectangle: Rectangle

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "obstacle_type": self.obstacle_type,
            "rectangle": self.rectangle.to_dict(),
        }