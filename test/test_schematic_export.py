import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.exporter.schematic_json_exporter import (
    SchematicJsonExporter,
)
from test_schematic_pipeline import (
    build_test_schematic,
)


def export_test_schematic() -> Path:
    """
    生成 Buck 原理图，并导出为 JSON。
    """

    circuit_graph = build_test_schematic()

    output_path = (
        PROJECT_ROOT
        / "output"
        / "schematic"
        / "buck_schematic.json"
    )

    exporter = SchematicJsonExporter()

    exported_path = exporter.export(
        circuit_graph=circuit_graph,
        output_path=output_path,
        topology="Buck",
    )

    return exported_path

import json


def validate_exported_json(
    file_path: Path,
) -> None:
    """
    重新读取 JSON，并验证关键内容。
    """

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        document = json.load(file)

    metadata = document["metadata"]
    statistics = document["statistics"]

    assert metadata["format"] == (
        "LLM-PCB-Schematic"
    )
    assert metadata["version"] == "1.0"
    assert metadata["topology"] == "Buck"

    assert statistics["component_count"] == 6
    assert statistics["pin_count"] == 14
    assert statistics["net_count"] == 5

    net_names = {
        net["name"]
        for net in document["nets"]
    }

    expected_nets = {
        "VIN",
        "SW",
        "VOUT",
        "FB",
        "GND",
    }

    assert net_names == expected_nets

    print("JSON validation passed.")

if __name__ == "__main__":
    path = export_test_schematic()

    print("=" * 60)
    print("SCHEMATIC JSON EXPORT")
    print("=" * 60)
    print(f"Export successful: {path}")

    validate_exported_json(path)