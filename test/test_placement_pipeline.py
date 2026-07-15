from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.pcb.placement import (
    TopologyAwarePlacementEngine,
)
from test_design_pipeline import (
    build_test_design,
)
from test_schematic_pipeline import (
    build_test_schematic,
)


def build_test_placement():
    """
    生成约束图、原理图与 PCB 初始布局。
    """

    constraint_graph = build_test_design()
    circuit_graph = build_test_schematic()

    placement_engine = (
        TopologyAwarePlacementEngine()
    )

    board = placement_engine.place_buck(
        circuit_graph=circuit_graph,
        constraint_graph=constraint_graph,
        board_width=100.0,
        board_height=80.0,
    )

    return board


if __name__ == "__main__":
    test_board = build_test_placement()
    test_board.show()

    validator = TopologyAwarePlacementEngine()

    violations = validator.validate_buck_placement(
        test_board
    )

    print("\nPlacement Validation:")

    if violations:
        for violation in violations:
            print("-", violation)
    else:
        print("Placement validation passed.")