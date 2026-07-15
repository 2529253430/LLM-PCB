import json
from pathlib import Path
from typing import Any

from src.pcb.board import PCBBoard


class PlacementJsonExporter:
    """
    将 PCBBoard 布局结果导出为 JSON。
    """

    FORMAT_NAME = "LLM-PCB-Placement"
    FORMAT_VERSION = "1.0"

    def export(
        self,
        board: PCBBoard,
        output_path: Path,
        topology: str,
    ) -> Path:
        """
        导出 PCB 布局结果。
        """

        document = self.to_dict(
            board=board,
            topology=topology,
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                document,
                file,
                ensure_ascii=False,
                indent=2,
            )

        return output_path

    def to_dict(
        self,
        board: PCBBoard,
        topology: str,
    ) -> dict[str, Any]:
        """
        把 PCBBoard 转换为标准字典。
        """

        board_data = board.to_dict()

        return {
            "metadata": {
                "format": self.FORMAT_NAME,
                "version": self.FORMAT_VERSION,
                "topology": topology,
            },
            "board": board_data["board"],
            "components": board_data["components"],
            "statistics": board_data["statistics"],
        }