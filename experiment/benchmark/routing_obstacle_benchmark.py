import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DIR = PROJECT_ROOT / "test"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.pcb.board import PCBBoard
from src.pcb.manhattan_router import ManhattanRouter
from src.pcb.route import RoutingResult
from src.pcb.routing_plan import (
    NetRoutingPlan,
    RoutingEndpoint,
    RoutingPlan,
)
from src.pcb.visualizer import PCBRoutingVisualizer


def build_benchmark_board() -> PCBBoard:
    """
    创建一个故意存在障碍物的测试板。

    U1 和 L1 位于同一水平线上，
    C1 放在二者之间，迫使路线绕行。
    """

    board = PCBBoard(
        width=100.0,
        height=70.0,
        unit="mm",
    )

    board.place_component(
        reference="U1",
        component_type="Controller",
        x=20.0,
        y=35.0,
        width=12.0,
        height=10.0,
    )

    board.place_component(
        reference="C1",
        component_type="Obstacle Capacitor",
        x=50.0,
        y=35.0,
        width=16.0,
        height=18.0,
    )

    board.place_component(
        reference="L1",
        component_type="Inductor",
        x=80.0,
        y=35.0,
        width=12.0,
        height=12.0,
    )

    return board


def build_benchmark_routing_plan() -> RoutingPlan:
    """
    创建 U1 到 L1 的单网络测试计划。
    """

    routing_plan = RoutingPlan()

    sw_plan = NetRoutingPlan(
        net_name="SW",
        endpoints=[
            RoutingEndpoint(
                reference="U1",
                pin_number="SW",
                pin_name="SW",
                x=20.0,
                y=35.0,
            ),
            RoutingEndpoint(
                reference="L1",
                pin_number="1",
                pin_name="IN",
                x=80.0,
                y=35.0,
            ),
        ],
        priority=1,
        preferred_width=2.0,
        strategy="Horizontal First",
        preferred_layer="Top",
        avoid_nets=[],
        rule_texts=[
            "Keep trace as short as possible."
        ],
    )

    routing_plan.add_net_plan(sw_plan)

    return routing_plan


def build_naive_result(
    routing_plan: RoutingPlan,
) -> RoutingResult:
    """
    不提供 board，因此不进行障碍物检测。
    """

    router = ManhattanRouter()

    return router.route(
        routing_plan=routing_plan,
        board=None,
    )


def build_obstacle_aware_result(
    routing_plan: RoutingPlan,
    board: PCBBoard,
) -> RoutingResult:
    """
    提供 board，启用障碍检测与 detour。
    """

    router = ManhattanRouter(
        obstacle_clearance=1.0,
        detour_clearance=2.0,
    )

    return router.route(
        routing_plan=routing_plan,
        board=board,
    )


def route_collides_with_board(
    routing_result: RoutingResult,
    board: PCBBoard,
) -> bool:
    """
    检查 SW 路径是否与 C1 障碍物碰撞。
    """

    obstacles = board.build_component_obstacles(
        clearance=1.0
    )

    obstacle_map = {
        obstacle.reference: obstacle
        for obstacle in obstacles
    }

    c1_obstacle = obstacle_map["C1"]

    sw_route = routing_result.get_routed_net("SW")

    detector = ManhattanRouter().detector

    for connection in sw_route.connections:
        for segment in connection.segments:
            if detector.segment_intersects_obstacle(
                segment=segment,
                obstacle=c1_obstacle,
            ):
                return True

    return False


def collect_metrics(
    naive_result: RoutingResult,
    obstacle_result: RoutingResult,
    board: PCBBoard,
) -> dict[str, Any]:
    """
    收集论文实验所需指标。
    """

    naive_net = naive_result.get_routed_net("SW")
    obstacle_net = obstacle_result.get_routed_net("SW")

    naive_connection = naive_net.connections[0]
    obstacle_connection = obstacle_net.connections[0]

    return {
        "benchmark": "single_rectangular_obstacle",
        "naive_manhattan": {
            "total_length_mm": (
                naive_connection.total_length()
            ),
            "segment_count": len(
                naive_connection.segments
            ),
            "point_count": len(
                naive_connection.points
            ),
            "collision": route_collides_with_board(
                routing_result=naive_result,
                board=board,
            ),
        },
        "obstacle_aware": {
            "total_length_mm": (
                obstacle_connection.total_length()
            ),
            "segment_count": len(
                obstacle_connection.segments
            ),
            "point_count": len(
                obstacle_connection.points
            ),
            "collision": route_collides_with_board(
                routing_result=obstacle_result,
                board=board,
            ),
        },
    }


def save_results(
    metrics: dict[str, Any],
) -> Path:
    """
    保存实验结果 JSON。
    """

    output_path = (
        PROJECT_ROOT
        / "experiment"
        / "results"
        / "routing_benchmark.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def save_figures(
    board: PCBBoard,
    naive_result: RoutingResult,
    obstacle_result: RoutingResult,
) -> tuple[Path, Path]:
    """
    保存两张对比图。
    """

    figure_dir = (
        PROJECT_ROOT
        / "paper"
        / "figures"
    )

    figure_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    naive_path = (
        figure_dir
        / "benchmark_naive_manhattan.png"
    )

    obstacle_path = (
        figure_dir
        / "benchmark_obstacle_aware.png"
    )

    visualizer = PCBRoutingVisualizer()

    visualizer.save(
        board=board,
        routing_result=naive_result,
        output_path=naive_path,
        title="Naive Manhattan Routing",
    )

    visualizer.save(
        board=board,
        routing_result=obstacle_result,
        output_path=obstacle_path,
        title="Obstacle-Aware Manhattan Routing",
    )

    return naive_path, obstacle_path


def validate_metrics(
    metrics: dict[str, Any],
) -> None:
    """
    验证基准实验符合预期。
    """

    naive = metrics["naive_manhattan"]
    obstacle = metrics["obstacle_aware"]

    assert naive["collision"] is True
    assert obstacle["collision"] is False

    assert obstacle["total_length_mm"] > (
        naive["total_length_mm"]
    )

    assert obstacle["segment_count"] >= 3
    assert naive["segment_count"] == 1

    print("Routing benchmark validation passed.")


if __name__ == "__main__":
    board = build_benchmark_board()
    routing_plan = build_benchmark_routing_plan()

    naive_result = build_naive_result(
        routing_plan
    )

    obstacle_result = (
        build_obstacle_aware_result(
            routing_plan=routing_plan,
            board=board,
        )
    )

    metrics = collect_metrics(
        naive_result=naive_result,
        obstacle_result=obstacle_result,
        board=board,
    )

    results_path = save_results(metrics)

    naive_figure, obstacle_figure = (
        save_figures(
            board=board,
            naive_result=naive_result,
            obstacle_result=obstacle_result,
        )
    )

    validate_metrics(metrics)

    print("=" * 60)
    print("ROUTING OBSTACLE BENCHMARK")
    print("=" * 60)

    print(json.dumps(
        metrics,
        ensure_ascii=False,
        indent=2,
    ))

    print(f"\nResults: {results_path}")
    print(f"Naive figure: {naive_figure}")
    print(
        f"Obstacle-aware figure: "
        f"{obstacle_figure}"
    )