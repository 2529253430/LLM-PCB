import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.exporter.routing_result_exporter import (
    RoutingResultExporter,
)
from src.pcb.visualizer import (
    PCBRoutingVisualizer,
)
from test_manhattan_routing import (
    build_test_routing_result,
)
from test_placement_pipeline import (
    build_test_placement,
)


if __name__ == "__main__":
    board = build_test_placement()
    routing_result = (
        build_test_routing_result()
    )

    json_path = (
        PROJECT_ROOT
        / "output"
        / "routing"
        / "buck_routes.json"
    )

    image_path = (
        PROJECT_ROOT
        / "output"
        / "routing"
        / "buck_routed_board.png"
    )

    exporter = RoutingResultExporter()

    exported_json = exporter.export(
        routing_result=routing_result,
        output_path=json_path,
    )

    visualizer = PCBRoutingVisualizer()

    exported_image = visualizer.save(
        board=board,
        routing_result=routing_result,
        output_path=image_path,
        title=(
            "Constraint-Aware Manhattan "
            "Routing for Buck Converter"
        ),
    )

    with exported_json.open(
        "r",
        encoding="utf-8",
    ) as file:
        document = json.load(file)

    assert document["metadata"]["format"] == (
        "LLM-PCB-Routing"
    )
    assert document["metadata"]["router"] == (
        "ManhattanRouter"
    )
    assert document["statistics"]["net_count"] == 5
    assert (
        document["statistics"]["total_length"]
        > 0
    )

    print("=" * 60)
    print("PCB ROUTING EXPORT")
    print("=" * 60)
    print(
        f"Routing JSON exported to: "
        f"{exported_json}"
    )
    print(
        f"Routed board image exported to: "
        f"{exported_image}"
    )
    print(
        "Routing export validation passed."
    )