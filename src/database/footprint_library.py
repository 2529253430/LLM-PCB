import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

FOOTPRINT_LIBRARY_DIR = (
    PROJECT_ROOT
    / "data"
    / "libraries"
    / "footprints"
)


class FootprintLibrary:
    """
    读取和验证 PCB 封装定义。
    """

    def __init__(
        self,
        library_dir: Path = FOOTPRINT_LIBRARY_DIR,
    ) -> None:
        self.library_dir = library_dir

    def load_footprint(
        self,
        footprint_name: str,
    ) -> dict[str, Any]:
        """
        根据封装名称读取 JSON 文件。
        """

        normalized_name = (
            footprint_name
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        aliases = {
            "soic_8_powerpad_dda": "soic8_powerpad_dda",
            "soic8_powerpad_dda": "soic8_powerpad_dda",
        }

        file_name = aliases.get(
            normalized_name,
            normalized_name,
        )

        candidate_paths = [
            self.library_dir / f"{file_name}.json",
            self.library_dir
            / f"{footprint_name.strip().lower()}.json",
        ]

        for file_path in candidate_paths:
            if file_path.exists():
                return self._load_json(file_path)

        raise FileNotFoundError(
            "Footprint library entry not found: "
            f"{footprint_name}\n"
            f"Library directory: {self.library_dir}\n"
            f"Tried files: "
            f"{[str(path) for path in candidate_paths]}"
        )

    def validate_footprint(
        self,
        footprint_data: dict[str, Any],
    ) -> list[str]:
        """
        检查封装数据是否完整。
        """

        errors: list[str] = []

        required_fields = {
            "footprint_name",
            "unit",
            "body",
            "pads",
        }

        for field_name in required_fields:
            if field_name not in footprint_data:
                errors.append(
                    f"Missing field: {field_name}"
                )

        body = footprint_data.get("body", {})

        if not isinstance(body, dict):
            errors.append(
                "Body must be an object."
            )
        else:
            if float(body.get("width", 0)) <= 0:
                errors.append(
                    "Body width must be greater than 0."
                )

            if float(body.get("length", 0)) <= 0:
                errors.append(
                    "Body length must be greater than 0."
                )

        pads = footprint_data.get("pads", [])

        if not isinstance(pads, list):
            errors.append(
                "Pads must be a list."
            )
            return errors

        pad_numbers: set[str] = set()

        for pad in pads:
            number = str(
                pad.get("number", "")
            ).strip()

            if not number:
                errors.append(
                    "A pad has no number."
                )
                continue

            if number in pad_numbers:
                errors.append(
                    f"Duplicate pad number: {number}"
                )

            pad_numbers.add(number)

            for dimension_name in (
                "width",
                "height",
            ):
                dimension_value = float(
                    pad.get(
                        dimension_name,
                        0,
                    )
                )

                if dimension_value <= 0:
                    errors.append(
                        f"Pad {number} "
                        f"{dimension_name} must be "
                        "greater than 0."
                    )

            for coordinate_name in (
                "x",
                "y",
            ):
                if coordinate_name not in pad:
                    errors.append(
                        f"Pad {number} missing "
                        f"coordinate: {coordinate_name}"
                    )

        return errors

    @staticmethod
    def get_pad(
        footprint_data: dict[str, Any],
        pad_number: str,
    ) -> dict[str, Any]:
        """
        根据焊盘编号查找 Pad。
        """

        normalized_number = str(
            pad_number
        ).strip()

        for pad in footprint_data.get(
            "pads",
            [],
        ):
            if str(
                pad.get("number", "")
            ).strip() == normalized_number:
                return pad

        raise KeyError(
            f"Pad not found: {pad_number}"
        )

    @staticmethod
    def get_absolute_pad_position(
        footprint_data: dict[str, Any],
        pad_number: str,
        component_x: float,
        component_y: float,
    ) -> tuple[float, float]:
        """
        计算 Pad 在 PCB 上的绝对坐标。

        当前版本假设元件旋转角度为 0°。
        """

        pad = FootprintLibrary.get_pad(
            footprint_data,
            pad_number,
        )

        absolute_x = (
            component_x
            + float(pad["x"])
        )

        absolute_y = (
            component_y
            + float(pad["y"])
        )

        return (
            absolute_x,
            absolute_y,
        )

    @staticmethod
    def _load_json(
        file_path: Path,
    ) -> dict[str, Any]:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)