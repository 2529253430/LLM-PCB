from pathlib import Path
import sys
from test_placement_pipeline import (
    build_test_placement,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.pcb.manhattan_router import (
    ManhattanRouter,
)
from test_routing_plan import (
    build_test_routing_plan,
)


def build_test_routing_result():
    """
    建立 Routing Plan 并完成几何布线。
    """

    routing_plan = build_test_routing_plan()

    router = ManhattanRouter()

    board = build_test_placement()

    routing_result = router.route(
    routing_plan=routing_plan,
    board=board,
    )

    return routing_result


def validate_routing_result() -> None:
    """
    验证关键网络的布线路径。
    """

    routing_result = (
        build_test_routing_result()
    )

    assert len(
        routing_result.routed_nets
    ) == 5

    sw_route = routing_result.get_routed_net(
        "SW"
    )

    assert len(sw_route.connections) == 1
    assert sw_route.preferred_width == 2.0
    assert sw_route.preferred_layer == "Top"

    sw_connection = sw_route.connections[0]

    assert (
        sw_connection.source_reference
        == "U1"
    )
    assert (
        sw_connection.target_reference
        == "L1"
    )

    for routed_net in (
        routing_result.routed_nets.values()
    ):
        for connection in (
            routed_net.connections
        ):
            for segment in connection.segments:
                assert (
                    segment.is_horizontal()
                    or segment.is_vertical()
                )

    assert routing_result.total_length() > 0

    print(
        "Manhattan routing validation passed."
    )


if __name__ == "__main__":
    result = build_test_routing_result()

    result.show()

    print()
    validate_routing_result()