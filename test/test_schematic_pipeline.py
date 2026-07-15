from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.schematic.schematic_generator import SchematicGenerator
from test_design_pipeline import build_test_design


def build_test_schematic():
    constraint_graph = build_test_design()

    generator = SchematicGenerator()

    circuit_graph = generator.generate_buck(
        constraint_graph=constraint_graph
    )

    return circuit_graph


if __name__ == "__main__":
    schematic = build_test_schematic()
    schematic.show()