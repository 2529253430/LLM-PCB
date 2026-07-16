from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from src.database.component_library import (
    ComponentLibrary,
)
from src.database.footprint_library import (
    FootprintLibrary,
)


@dataclass(frozen=True)
class PadPosition:
    """
    PCB 上一个焊盘的实际位置。
    """

    pad_number: str
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "pad_number": self.pad_number,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


class ComponentInstance:
    """
    PCB 上一个具体器件实例。

    例如：
    U1 是 TPS5430DDA 在当前 PCB 上的一个实例。
    """

    def __init__(
        self,
        reference: str,
        part_number: str,
        x: float,
        y: float,
        rotation: float = 0.0,
    ) -> None:
        if not reference.strip():
            raise ValueError(
                "Component reference cannot be empty."
            )

        if not part_number.strip():
            raise ValueError(
                "Part number cannot be empty."
            )

        self.reference = reference.strip()
        self.part_number = part_number.strip()
        self.x = float(x)
        self.y = float(y)
        self.rotation = float(rotation) % 360.0

        self.component_library = (
            ComponentLibrary()
        )

        self.footprint_library = (
            FootprintLibrary()
        )

        self.part_data = (
            self.component_library.load_part(
                self.part_number
            )
        )

        part_errors = (
            self.component_library.validate_part(
                self.part_data
            )
        )

        if part_errors:
            raise ValueError(
                "Invalid component library entry: "
                + "; ".join(part_errors)
            )

        footprint_name = str(
            self.part_data["footprint_name"]
        )

        self.footprint_data = (
            self.footprint_library.load_footprint(
                footprint_name
            )
        )

        footprint_errors = (
            self.footprint_library
            .validate_footprint(
                self.footprint_data
            )
        )

        if footprint_errors:
            raise ValueError(
                "Invalid footprint library entry: "
                + "; ".join(footprint_errors)
            )

        self._validate_pin_pad_mapping()

    def get_pad_position(
        self,
        pad_number: str,
    ) -> PadPosition:
        """
        获取某个 Pad 的 PCB 绝对坐标。

        支持元件旋转。
        """

        pad = self.footprint_library.get_pad(
            footprint_data=self.footprint_data,
            pad_number=pad_number,
        )

        local_x = float(pad["x"])
        local_y = float(pad["y"])

        rotated_x, rotated_y = (
            self._rotate_local_coordinate(
                local_x=local_x,
                local_y=local_y,
            )
        )

        return PadPosition(
            pad_number=str(pad["number"]),
            x=self.x + rotated_x,
            y=self.y + rotated_y,
            width=float(pad["width"]),
            height=float(pad["height"]),
        )

    def get_pads_by_logical_role(
        self,
        logical_role: str,
    ) -> list[PadPosition]:
        """
        根据逻辑角色查询真实焊盘。

        例如：
        SW -> Pad 7 和 Pad 8
        GND -> Pad 5 和 Pad 9
        """

        matching_pins = (
            self.component_library
            .get_pin_by_role(
                part_data=self.part_data,
                logical_role=logical_role,
            )
        )

        pad_positions = []

        for pin in matching_pins:
            pad_number = str(
                pin["number"]
            )

            pad_positions.append(
                self.get_pad_position(
                    pad_number
                )
            )

        return pad_positions

    def get_primary_pad_by_role(
        self,
        logical_role: str,
    ) -> PadPosition:
        """
        返回某个逻辑角色的首选焊盘。

        第一版路由器先使用第一个匹配焊盘。
        """

        pads = self.get_pads_by_logical_role(
            logical_role
        )

        if not pads:
            raise KeyError(
                "No pad found for logical role: "
                f"{logical_role}"
            )

        return pads[0]

    def get_all_pad_positions(
        self,
    ) -> list[PadPosition]:
        """
        获取该器件的全部焊盘坐标。
        """

        pad_positions = []

        for pad in self.footprint_data.get(
            "pads",
            [],
        ):
            pad_positions.append(
                self.get_pad_position(
                    str(pad["number"])
                )
            )

        return pad_positions

    def to_dict(self) -> dict[str, Any]:
        """
        转换为后续 EDA 导出使用的字典。
        """

        return {
            "reference": self.reference,
            "part_number": self.part_number,
            "symbol_name": self.part_data.get(
                "symbol_name",
                "",
            ),
            "footprint_name": (
                self.part_data.get(
                    "footprint_name",
                    "",
                )
            ),
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "pads": [
                pad.to_dict()
                for pad in (
                    self.get_all_pad_positions()
                )
            ],
        }

    def _validate_pin_pad_mapping(
        self,
    ) -> None:
        """
        检查每个物理引脚是否存在对应 Pad。
        """

        footprint_pad_numbers = {
            str(pad.get("number", "")).strip()
            for pad in self.footprint_data.get(
                "pads",
                [],
            )
        }

        missing_pad_numbers = []

        for pin in self.part_data.get(
            "pins",
            [],
        ):
            pin_number = str(
                pin.get("number", "")
            ).strip()

            if (
                pin_number
                not in footprint_pad_numbers
            ):
                missing_pad_numbers.append(
                    pin_number
                )

        if missing_pad_numbers:
            raise ValueError(
                "Component pins have no matching "
                "footprint pads: "
                f"{missing_pad_numbers}"
            )

    def _rotate_local_coordinate(
        self,
        local_x: float,
        local_y: float,
    ) -> tuple[float, float]:
        """
        将封装局部坐标按器件旋转角度旋转。

        支持任意角度，当前主要使用：
        0°、90°、180°、270°。
        """

        angle_radians = math.radians(
            self.rotation
        )

        cosine = math.cos(angle_radians)
        sine = math.sin(angle_radians)

        rotated_x = (
            local_x * cosine
            - local_y * sine
        )

        rotated_y = (
            local_x * sine
            + local_y * cosine
        )

        # 避免出现非常小的浮点误差，例如
        # 2.0000000000000004。
        return (
            round(rotated_x, 6),
            round(rotated_y, 6),
        )