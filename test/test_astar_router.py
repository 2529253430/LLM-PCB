from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pcb.astar_router import AStarGridRouter
from src.pcb.board import PCBBoard
from src.pcb.routing_plan import (
    NetRoutingPlan,
    RoutingEndpoint,
    RoutingPlan,
)
from src.pcb.visualizer import (
    PCBRoutingVisualizer,
)

def build_multi_obstacle_board() -> PCBBoard:
    """
    在起点和终点之间设置多个交错障碍物。
    """

    board = PCBBoard(
        width=100.0,
        height=80.0,
        unit="mm",
    )

    board.place_component(
        reference="U1",
        component_type="Source",
        x=10.0,
        y=40.0,
        width=8.0,
        height=8.0,
    )

    board.place_component(
        reference="C1",
        component_type="Obstacle",
        x=35.0,
        y=32.0,
        width=14.0,
        height=28.0,
    )

    board.place_component(
        reference="C2",
        component_type="Obstacle",
        x=58.0,
        y=50.0,
        width=14.0,
        height=28.0,
    )

    board.place_component(
        reference="L1",
        component_type="Target",
        x=90.0,
        y=40.0,
        width=8.0,
        height=8.0,
    )

    return board


def build_astar_test_plan() -> RoutingPlan:
    plan = RoutingPlan()

    plan.add_net_plan(
        NetRoutingPlan(
            net_name="SW",
            endpoints=[
                RoutingEndpoint(
                    reference="U1",
                    pin_number="SW",
                    pin_name="SW",
                    x=10.0,
                    y=40.0,
                ),
                RoutingEndpoint(
                    reference="L1",
                    pin_number="1",
                    pin_name="IN",
                    x=90.0,
                    y=40.0,
                ),
            ],
            priority=1,
            preferred_width=2.0,
            strategy="Horizontal First",
            preferred_layer="Top",
        )
    )

    return plan


def build_astar_result():
    board = build_multi_obstacle_board()
    routing_plan = build_astar_test_plan()

    router = AStarGridRouter(
        grid_size=2.0,
        obstacle_clearance=1.0,
    )

    result = router.route(
        routing_plan=routing_plan,
        board=board,
    )

    return board, result


def validate_astar_result() -> None:
    board, result = build_astar_result()

    routed_net = result.get_routed_net("SW")

    assert len(routed_net.connections) == 1

    connection = routed_net.connections[0]

    assert connection.total_length() > 80.0
    assert len(connection.segments) >= 3

    obstacles = board.build_component_obstacles(
        clearance=1.0
    )

    obstacle_references = {
        obstacle.reference: obstacle
        for obstacle in obstacles
    }

    from src.pcb.obstacle_detector import (
        ObstacleDetector,
    )

    detector = ObstacleDetector()

    for segment in connection.segments:
        for reference in ("C1", "C2"):
            assert not (
                detector.segment_intersects_obstacle(
                    segment=segment,
                    obstacle=obstacle_references[
                        reference
                    ],
                )
            )

    print("A* routing validation passed.")


if __name__ == "__main__":
    board, routing_result = (
        build_astar_result()
    )

    routing_result.show()

    print()
    validate_astar_result()

    image_path = (
        PROJECT_ROOT
        / "paper"
        / "figures"
        / "astar_multi_obstacle_routing.png"
    )

    visualizer = PCBRoutingVisualizer()

    visualizer.save(
        board=board,
        routing_result=routing_result,
        output_path=image_path,
        title=(
            "A* Multi-Obstacle "
            "PCB Routing"
        ),
    )

    print(
        f"A* routing figure: {image_path}"
    )