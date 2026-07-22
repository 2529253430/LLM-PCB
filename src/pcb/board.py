from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.pcb.obstacle import PCBObstacle, Rectangle


@dataclass
class PlacedComponent:
    """
    PCB 上已经放置的元件。
    """

    reference: str
    component_type: str
    x: float
    y: float
    rotation: float = 0.0
    width: float = 10.0
    height: float = 10.0
    part_number: str = ""
    footprint_name: str = ""
    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        规范化并验证元件数据。
        """

        self.reference = self.reference.strip()
        self.component_type = (
            self.component_type.strip()
        )
        self.part_number = (
            self.part_number.strip()
        )
        self.footprint_name = (
            self.footprint_name.strip()
        )

        if not self.reference:
            raise ValueError(
                "Component reference cannot be empty."
            )

        if not self.component_type:
            raise ValueError(
                "Component type cannot be empty."
            )

        if self.width <= 0:
            raise ValueError(
                "Component width must be greater than 0."
            )

        if self.height <= 0:
            raise ValueError(
                "Component height must be greater than 0."
            )

        self.rotation = (
            float(self.rotation) % 360.0
        )

    def to_dict(self) -> dict[str, Any]:
        """
        转换成可导出到 JSON 的字典。
        """

        return {
            "reference": self.reference,
            "component_type": self.component_type,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "width": self.width,
            "height": self.height,
            "part_number": self.part_number,
            "footprint_name": self.footprint_name,
            "attributes": self.attributes,
        }


class PCBBoard:
    """
    保存 PCB 尺寸与元件布局结果。
    """

    def __init__(
        self,
        width: float = 100.0,
        height: float = 80.0,
        unit: str = "mm",
    ) -> None:
        if width <= 0:
            raise ValueError(
                "Board width must be greater than 0."
            )

        if height <= 0:
            raise ValueError(
                "Board height must be greater than 0."
            )

        normalized_unit = unit.strip()

        if not normalized_unit:
            raise ValueError(
                "Board unit cannot be empty."
            )

        self.width = float(width)
        self.height = float(height)
        self.unit = normalized_unit

        self.components: dict[
            str,
            PlacedComponent,
        ] = {}

    def place_component(
        self,
        reference: str,
        component_type: str,
        x: float,
        y: float,
        rotation: float = 0.0,
        width: float = 10.0,
        height: float = 10.0,
        part_number: str = "",
        footprint_name: str = "",
        **attributes: Any,
    ) -> None:
        """
        在 PCB 上放置一个元件。
        """

        normalized_reference = (
            reference.strip()
        )

        if not normalized_reference:
            raise ValueError(
                "Component reference cannot be empty."
            )

        if (
            normalized_reference
            in self.components
        ):
            raise ValueError(
                "Component is already placed: "
                f"{normalized_reference}"
            )

        if width <= 0:
            raise ValueError(
                "Component width must be greater than 0."
            )

        if height <= 0:
            raise ValueError(
                "Component height must be greater than 0."
            )

        self._validate_position(
            x=x,
            y=y,
            component_width=width,
            component_height=height,
        )

        self.components[
            normalized_reference
        ] = PlacedComponent(
            reference=normalized_reference,
            component_type=component_type,
            x=float(x),
            y=float(y),
            rotation=float(rotation),
            width=float(width),
            height=float(height),
            part_number=part_number,
            footprint_name=footprint_name,
            attributes=dict(attributes),
        )

    def get_component(
        self,
        reference: str,
    ) -> PlacedComponent:
        """
        查询一个已经放置的元件。
        """

        normalized_reference = (
            reference.strip()
        )

        if (
            normalized_reference
            not in self.components
        ):
            raise KeyError(
                "Component is not placed: "
                f"{normalized_reference}"
            )

        return self.components[
            normalized_reference
        ]

    def build_component_obstacles(
        self,
        clearance: float = 0.0,
    ) -> list[PCBObstacle]:
        """
        把所有已放置元件转换为矩形障碍物。
        """

        if clearance < 0:
            raise ValueError(
                "Clearance cannot be negative."
            )

        obstacles: list[
            PCBObstacle
        ] = []

        for component in (
            self.components.values()
        ):
            half_width = (
                component.width / 2
            )

            half_height = (
                component.height / 2
            )

            rectangle = Rectangle(
                left=(
                    component.x
                    - half_width
                    - clearance
                ),
                right=(
                    component.x
                    + half_width
                    + clearance
                ),
                bottom=(
                    component.y
                    - half_height
                    - clearance
                ),
                top=(
                    component.y
                    + half_height
                    + clearance
                ),
            )

            obstacles.append(
                PCBObstacle(
                    reference=(
                        component.reference
                    ),
                    obstacle_type="Component",
                    rectangle=rectangle,
                )
            )

        return obstacles

    def get_distance(
        self,
        first_reference: str,
        second_reference: str,
    ) -> float:
        """
        计算两个元件中心之间的欧氏距离。
        """

        first = self.get_component(
            first_reference
        )

        second = self.get_component(
            second_reference
        )

        delta_x = first.x - second.x
        delta_y = first.y - second.y

        return (
            delta_x ** 2
            + delta_y ** 2
        ) ** 0.5

    def find_overlaps(
        self,
    ) -> list[tuple[str, str]]:
        """
        查找互相重叠的元件。
        """

        overlaps: list[
            tuple[str, str]
        ] = []

        component_list = list(
            self.components.values()
        )

        for first_index in range(
            len(component_list)
        ):
            first = component_list[
                first_index
            ]

            for second_index in range(
                first_index + 1,
                len(component_list),
            ):
                second = component_list[
                    second_index
                ]

                if self._components_overlap(
                    first,
                    second,
                ):
                    overlaps.append(
                        (
                            first.reference,
                            second.reference,
                        )
                    )

        return overlaps

    @staticmethod
    def _components_overlap(
        first: PlacedComponent,
        second: PlacedComponent,
    ) -> bool:
        """
        判断两个矩形元件是否重叠。

        当前版本暂不考虑旋转后的边界变化。
        """

        first_left = (
            first.x
            - first.width / 2
        )

        first_right = (
            first.x
            + first.width / 2
        )

        first_bottom = (
            first.y
            - first.height / 2
        )

        first_top = (
            first.y
            + first.height / 2
        )

        second_left = (
            second.x
            - second.width / 2
        )

        second_right = (
            second.x
            + second.width / 2
        )

        second_bottom = (
            second.y
            - second.height / 2
        )

        second_top = (
            second.y
            + second.height / 2
        )

        separated = (
            first_right <= second_left
            or second_right <= first_left
            or first_top <= second_bottom
            or second_top <= first_bottom
        )

        return not separated

    def to_dict(self) -> dict[str, Any]:
        """
        转换成可导出的 PCB 数据。
        """

        return {
            "board": {
                "width": self.width,
                "height": self.height,
                "unit": self.unit,
            },
            "components": [
                component.to_dict()
                for component in (
                    self.components.values()
                )
            ],
            "statistics": {
                "component_count": len(
                    self.components
                ),
            },
        }

    def show(self) -> None:
        """
        在终端打印布局结果。
        """

        print("=" * 60)
        print("PCB PLACEMENT")
        print("=" * 60)

        print(
            f"\nBoard: {self.width} × "
            f"{self.height} {self.unit}"
        )

        print("\nPlaced Components:")

        for component in (
            self.components.values()
        ):
            component_identity = (
                component.part_number
                or component.component_type
            )

            footprint_display = (
                component.footprint_name
                or "N/A"
            )

            print(
                f"- {component.reference}: "
                f"{component_identity}, "
                f"position=("
                f"{component.x}, "
                f"{component.y}), "
                f"rotation="
                f"{component.rotation}, "
                f"footprint="
                f"{footprint_display}"
            )

        print("\nStatistics:")

        print(
            f"- Components: "
            f"{len(self.components)}"
        )

    def _validate_position(
        self,
        x: float,
        y: float,
        component_width: float,
        component_height: float,
    ) -> None:
        """
        检查元件是否位于板框内部。
        """

        half_width = (
            component_width / 2
        )

        half_height = (
            component_height / 2
        )

        if x - half_width < 0:
            raise ValueError(
                "Component exceeds left "
                "board boundary."
            )

        if y - half_height < 0:
            raise ValueError(
                "Component exceeds bottom "
                "board boundary."
            )

        if x + half_width > self.width:
            raise ValueError(
                "Component exceeds right "
                "board boundary."
            )

        if y + half_height > self.height:
            raise ValueError(
                "Component exceeds top "
                "board boundary."
            )