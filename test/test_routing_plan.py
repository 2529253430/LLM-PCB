from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.pcb.routing_planner import (
    ConstraintAwareRoutingPlanner,
)
from test_design_pipeline import (
    build_test_design,
)
from test_placement_pipeline import (
    build_test_placement,
)
from test_schematic_pipeline import (
    build_test_schematic,
)


def build_test_routing_plan():
    """
    建立完整的 Buck 布线计划。
    """

    constraint_graph = build_test_design()
    circuit_graph = build_test_schematic()
    board = build_test_placement()

    planner = ConstraintAwareRoutingPlanner()

    routing_plan = planner.create_plan(
        circuit_graph=circuit_graph,
        constraint_graph=constraint_graph,
        board=board,
    )

    return routing_plan


def validate_routing_plan() -> None:
    """
    验证关键网络的规划结果。
    """

    plan = build_test_routing_plan()

    sw_plan = plan.get_net_plan("SW")
    vin_plan = plan.get_net_plan("VIN")
    fb_plan = plan.get_net_plan("FB")

    assert sw_plan.priority == 1
    assert sw_plan.preferred_width == 2.0
    assert "FB" in sw_plan.avoid_nets

    assert vin_plan.priority == 2
    assert vin_plan.preferred_width == 2.0

    assert fb_plan.priority == 4
    assert fb_plan.preferred_width == 0.3
    assert "SW" in fb_plan.avoid_nets

    assert len(plan.net_plans) == 5

    print("Routing plan validation passed.")


if __name__ == "__main__":
    test_plan = build_test_routing_plan()
    test_plan.show()

    print()
    validate_routing_plan()