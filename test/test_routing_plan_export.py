import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.exporter.routing_plan_exporter import (
    RoutingPlanExporter,
)
from test_routing_plan import (
    build_test_routing_plan,
)


if __name__ == "__main__":
    routing_plan = build_test_routing_plan()

    output_path = (
        PROJECT_ROOT
        / "output"
        / "routing"
        / "buck_routing_plan.json"
    )

    exporter = RoutingPlanExporter()

    exported_path = exporter.export(
        routing_plan=routing_plan,
        output_path=output_path,
    )

    with exported_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        document = json.load(file)

    assert document["metadata"]["format"] == (
        "LLM-PCB-Routing-Plan"
    )
    assert document["statistics"]["net_count"] == 5

    print(
        f"Routing plan exported to: "
        f"{exported_path}"
    )
    print("Routing plan JSON validation passed.")