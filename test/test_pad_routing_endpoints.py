from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.pcb.routing_planner import (
    ConstraintAwareRoutingPlanner,
)
from test_design_pipeline import build_test_design
from test_placement_pipeline import build_test_placement
from test_schematic_pipeline import build_test_schematic


if __name__ == "__main__":
    constraint_graph = build_test_design()
    circuit_graph = build_test_schematic()
    board = build_test_placement()

    planner = ConstraintAwareRoutingPlanner()

    routing_plan = planner.create_plan(
        circuit_graph=circuit_graph,
        constraint_graph=constraint_graph,
        board=board,
    )

    vin_plan = routing_plan.get_net_plan("VIN")
    sw_plan = routing_plan.get_net_plan("SW")
    fb_plan = routing_plan.get_net_plan("FB")
    gnd_plan = routing_plan.get_net_plan("GND")

    u1_vin = next(
        endpoint
        for endpoint in vin_plan.endpoints
        if endpoint.reference == "U1"
    )

    u1_sw = next(
        endpoint
        for endpoint in sw_plan.endpoints
        if endpoint.reference == "U1"
    )

    u1_fb = next(
        endpoint
        for endpoint in fb_plan.endpoints
        if endpoint.reference == "U1"
    )

    u1_gnd = next(
        endpoint
        for endpoint in gnd_plan.endpoints
        if endpoint.reference == "U1"
    )

    assert u1_vin.pin_number == "6"
    assert u1_sw.pin_number == "7"
    assert u1_fb.pin_number == "3"
    assert u1_gnd.pin_number == "5"

    assert (u1_vin.x, u1_vin.y) == (
        34.7,
        39.365,
    )

    assert (u1_sw.x, u1_sw.y) == (
        34.7,
        40.635,
    )

    assert (u1_fb.x, u1_fb.y) == (
        29.3,
        39.365,
    )

    assert (u1_gnd.x, u1_gnd.y) == (
        34.7,
        38.095,
    )

    print("=" * 60)
    print("PAD-LEVEL ROUTING ENDPOINTS")
    print("=" * 60)

    print("U1 VIN Pad 6:", u1_vin)
    print("U1 SW Pad 7:", u1_sw)
    print("U1 FB Pad 3:", u1_fb)
    print("U1 GND Pad 5:", u1_gnd)

    print(
        "Pad-level routing endpoint validation passed."
    )