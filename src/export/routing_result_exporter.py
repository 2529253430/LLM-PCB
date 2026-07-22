import json
from pathlib import Path

from src.pcb.route import RoutingResult


class RoutingResultExporter:
    """
    导出几何布线结果。
    """

    FORMAT_NAME = "LLM-PCB-Routing"
    FORMAT_VERSION = "1.0"

    def export(
        self,
        routing_result: RoutingResult,
        output_path: Path,
    ) -> Path:
        document = {
            "metadata": {
                "format": self.FORMAT_NAME,
                "version": self.FORMAT_VERSION,
                "router": "ManhattanRouter",
            },
            **routing_result.to_dict(),
        }

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
                indent=2,
                ensure_ascii=False,
            )

        return output_path