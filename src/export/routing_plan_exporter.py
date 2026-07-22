import json
from pathlib import Path

from src.pcb.routing_plan import RoutingPlan


class RoutingPlanExporter:
    """
    将 RoutingPlan 导出为 JSON。
    """

    def export(
        self,
        routing_plan: RoutingPlan,
        output_path: Path,
    ) -> Path:
        document = {
            "metadata": {
                "format": "LLM-PCB-Routing-Plan",
                "version": "1.0",
            },
            **routing_plan.to_dict(),
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