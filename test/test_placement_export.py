import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.exporter.placement_json_exporter import (
    PlacementJsonExporter,
)
from src.pcb.visualizer import (
    PCBPlacementVisualizer,
)
from test_placement_pipeline import (
    build_test_placement,
)


def export_test_placement() -> tuple[Path, Path]:
    """
    生成布局，并导出 JSON 和 PNG。
    """

    board = build_test_placement()

    json_output_path = (
        PROJECT_ROOT
        / "output"
        / "placement"
        / "buck_placement.json"
    )

    image_output_path = (
        PROJECT_ROOT
        / "output"
        / "placement"
        / "buck_placement.png"
    )

    json_exporter = PlacementJsonExporter()

    exported_json_path = json_exporter.export(
        board=board,
        output_path=json_output_path,
        topology="Buck",
    )

    visualizer = PCBPlacementVisualizer()

    exported_image_path = visualizer.save(
        board=board,
        output_path=image_output_path,
        title=(
            "Topology-Aware Buck "
            "PCB Placement"
        ),
    )

    return (
        exported_json_path,
        exported_image_path,
    )


def validate_placement_json(
    file_path: Path,
) -> None:
    """
    验证布局 JSON 的关键字段。
    """

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        document = json.load(file)

    assert document["metadata"]["format"] == (
        "LLM-PCB-Placement"
    )
    assert document["metadata"]["version"] == (
        "1.0"
    )
    assert document["metadata"]["topology"] == (
        "Buck"
    )

    assert document["board"]["width"] == 100.0
    assert document["board"]["height"] == 80.0
    assert document["board"]["unit"] == "mm"

    assert document["statistics"][
        "component_count"
    ] == 6

    references = {
        component["reference"]
        for component in document["components"]
    }

    expected_references = {
        "U1",
        "CIN",
        "L1",
        "COUT",
        "R1",
        "R2",
    }

    assert references == expected_references

    print("Placement JSON validation passed.")

def validate_no_overlap() -> None:
    """
    检查当前布局中没有元件重叠。
    """

    board = build_test_placement()

    overlaps = board.find_overlaps()

    assert not overlaps, (
        f"Overlapping components found: {overlaps}"
    )

    print("Placement overlap validation passed.")

if __name__ == "__main__":
    json_path, image_path = (
        export_test_placement()
    )

    print("=" * 60)
    print("PCB PLACEMENT EXPORT")
    print("=" * 60)

    print(f"JSON exported to: {json_path}")
    print(f"Image exported to: {image_path}")

    validate_placement_json(json_path)
    validate_no_overlap()