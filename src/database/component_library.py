import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent.parent
)

SYMBOL_LIBRARY_DIR = (
    PROJECT_ROOT
    / "data"
    / "libraries"
    / "symbols"
)


class ComponentLibrary:
    """
    读取并验证真实器件的符号、引脚和封装映射。
    """

    def __init__(
        self,
        library_dir: Path = SYMBOL_LIBRARY_DIR,
    ) -> None:
        self.library_dir = library_dir

    def load_part(
        self,
        part_number: str,
    ) -> dict[str, Any]:
        """
        根据器件型号加载 JSON 定义。
        """

        file_name = (
            part_number
            .strip()
            .lower()
            .replace("-", "")
        )

        candidate_paths = [
            self.library_dir
            / f"{file_name}.json",
            self.library_dir
            / f"{part_number.strip().lower()}.json",
        ]

        for file_path in candidate_paths:
            if file_path.exists():
                return self._load_json(file_path)

        # TPS5430DDA 与 tps5430.json 的临时别名。
        if part_number.upper().startswith(
            "TPS5430"
        ):
            alias_path = (
                self.library_dir
                / "tps5430.json"
            )

            if alias_path.exists():
                return self._load_json(alias_path)

        raise FileNotFoundError(
            "Component library entry not found: "
            f"{part_number}"
        )

    def get_pin_by_role(
        self,
        part_data: dict[str, Any],
        logical_role: str,
    ) -> list[dict[str, Any]]:
        """
        根据逻辑角色查找真实物理引脚。

        例如：
        SW -> Pin 7 和 Pin 8
        GND -> Pin 5 和 PowerPAD
        """

        normalized_role = (
            logical_role.strip().upper()
        )

        return [
            pin
            for pin in part_data.get(
                "pins",
                [],
            )
            if str(
                pin.get("logical_role", "")
            ).strip().upper()
            == normalized_role
        ]

    def validate_part(
        self,
        part_data: dict[str, Any],
    ) -> list[str]:
        """
        检查器件数据是否包含关键字段。
        """

        errors = []

        required_fields = {
            "part_number",
            "manufacturer",
            "symbol_name",
            "footprint_name",
            "pins",
        }

        for field_name in required_fields:
            if field_name not in part_data:
                errors.append(
                    f"Missing field: {field_name}"
                )

        pins = part_data.get("pins", [])

        if not isinstance(pins, list):
            errors.append(
                "Pins must be a list."
            )
            return errors

        pin_numbers = set()

        for pin in pins:
            number = str(
                pin.get("number", "")
            ).strip()

            name = str(
                pin.get("name", "")
            ).strip()

            if not number:
                errors.append(
                    "A pin has no number."
                )

            if not name:
                errors.append(
                    f"Pin {number} has no name."
                )

            if number in pin_numbers:
                errors.append(
                    f"Duplicate pin number: {number}"
                )

            pin_numbers.add(number)

        return errors

    @staticmethod
    def _load_json(
        file_path: Path,
    ) -> dict[str, Any]:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)