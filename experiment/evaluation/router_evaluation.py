import csv
import json
from pathlib import Path
from time import perf_counter
import sys
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT))

from src.pcb.astar_router import AStarGridRouter
from src.pcb.board import PCBBoard
from src.pcb.manhattan_router import ManhattanRouter
from src.pcb.obstacle_detector import ObstacleDetector
from src.pcb.route import RoutingResult
from src.pcb.routing_plan import (
    NetRoutingPlan,
    RoutingEndpoint,
    RoutingPlan,
)


def build_single_obstacle_scenario(
) -> tuple[PCBBoard, RoutingPlan]:
    """
    单障碍物场景。

    U1 和 L1 位于同一水平线上，
    C1 放在二者之间。
    """

    board = PCBBoard(
        width=100.0,
        height=70.0,
        unit="mm",
    )

    board.place_component(
        reference="U1",
        component_type="Source",
        x=20.0,
        y=35.0,
        width=12.0,
        height=10.0,
    )

    board.place_component(
        reference="C1",
        component_type="Obstacle",
        x=50.0,
        y=35.0,
        width=16.0,
        height=18.0,
    )

    board.place_component(
        reference="L1",
        component_type="Target",
        x=80.0,
        y=35.0,
        width=12.0,
        height=12.0,
    )

    plan = RoutingPlan()

    plan.add_net_plan(
        NetRoutingPlan(
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
        )
    )

    return board, plan


def build_multi_obstacle_scenario(
) -> tuple[PCBBoard, RoutingPlan]:
    """
    多障碍物场景。

    两个障碍物交错排列，使简单的单次绕行
    更难找到可行路径。
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

    return board, plan


def count_collisions(
    routing_result: RoutingResult,
    board: PCBBoard,
) -> int:
    """
    统计走线与非起点、非终点元件的碰撞数量。
    """

    detector = ObstacleDetector()

    obstacles = board.build_component_obstacles(
        clearance=1.0
    )

    collisions: set[
        tuple[str, int, str]
    ] = set()

    for routed_net in (
        routing_result.routed_nets.values()
    ):
        for connection_index, connection in enumerate(
            routed_net.connections
        ):
            ignored_references = {
                connection.source_reference,
                connection.target_reference,
            }

            for segment_index, segment in enumerate(
                connection.segments
            ):
                segment_collisions = (
                    detector.find_collisions(
                        segment=segment,
                        obstacles=obstacles,
                        ignored_references=(
                            ignored_references
                        ),
                    )
                )

                for obstacle in segment_collisions:
                    collisions.add(
                        (
                            routed_net.net_name,
                            segment_index,
                            obstacle.reference,
                        )
                    )

    return len(collisions)


def count_segments(
    routing_result: RoutingResult,
) -> int:
    """
    统计所有走线线段数量。
    """

    return sum(
        len(connection.segments)
        for routed_net in (
            routing_result.routed_nets.values()
        )
        for connection in routed_net.connections
    )


def count_bends(
    routing_result: RoutingResult,
) -> int:
    """
    拐角数量 = 路径点数量减 2。

    两个点形成一条直线，没有拐角。
    """

    return sum(
        max(
            0,
            len(connection.points) - 2,
        )
        for routed_net in (
            routing_result.routed_nets.values()
        )
        for connection in routed_net.connections
    )


def evaluate_router(
    scenario_name: str,
    router_name: str,
    route_function: Callable[
        [],
        RoutingResult,
    ],
    board: PCBBoard,
) -> dict[str, Any]:
    """
    运行一个路由算法并收集指标。

    即使路由失败，也不会终止整个实验。
    """

    start_time = perf_counter()

    try:
        routing_result = route_function()

        elapsed_ms = (
            perf_counter() - start_time
        ) * 1000.0

        return {
            "scenario": scenario_name,
            "router": router_name,
            "success": True,
            "collision_count": count_collisions(
                routing_result,
                board,
            ),
            "total_length_mm": round(
                routing_result.total_length(),
                3,
            ),
            "segment_count": count_segments(
                routing_result
            ),
            "bend_count": count_bends(
                routing_result
            ),
            "runtime_ms": round(
                elapsed_ms,
                3,
            ),
            "error": "",
        }

    except Exception as error:
        elapsed_ms = (
            perf_counter() - start_time
        ) * 1000.0

        return {
            "scenario": scenario_name,
            "router": router_name,
            "success": False,
            "collision_count": None,
            "total_length_mm": None,
            "segment_count": None,
            "bend_count": None,
            "runtime_ms": round(
                elapsed_ms,
                3,
            ),
            "error": str(error),
        }


def evaluate_scenario(
    scenario_name: str,
    board: PCBBoard,
    routing_plan: RoutingPlan,
) -> list[dict[str, Any]]:
    """
    在同一个场景中评估三种路由器。
    """

    naive_router = ManhattanRouter()

    detour_router = ManhattanRouter(
        obstacle_clearance=1.0,
        detour_clearance=2.0,
    )

    astar_router = AStarGridRouter(
        grid_size=1.0,
        obstacle_clearance=1.0,
    )

    results = []

    results.append(
        evaluate_router(
            scenario_name=scenario_name,
            router_name="Naive Manhattan",
            route_function=lambda: (
                naive_router.route(
                    routing_plan=routing_plan,
                    board=None,
                )
            ),
            board=board,
        )
    )

    results.append(
        evaluate_router(
            scenario_name=scenario_name,
            router_name=(
                "Obstacle-Aware Manhattan"
            ),
            route_function=lambda: (
                detour_router.route(
                    routing_plan=routing_plan,
                    board=board,
                )
            ),
            board=board,
        )
    )

    results.append(
        evaluate_router(
            scenario_name=scenario_name,
            router_name="Grid A*",
            route_function=lambda: (
                astar_router.route(
                    routing_plan=routing_plan,
                    board=board,
                )
            ),
            board=board,
        )
    )

    return results


def run_evaluation() -> list[dict[str, Any]]:
    """
    运行全部实验场景。
    """

    all_results = []

    single_board, single_plan = (
        build_single_obstacle_scenario()
    )

    all_results.extend(
        evaluate_scenario(
            scenario_name="Single Obstacle",
            board=single_board,
            routing_plan=single_plan,
        )
    )

    multi_board, multi_plan = (
        build_multi_obstacle_scenario()
    )

    all_results.extend(
        evaluate_scenario(
            scenario_name="Multiple Obstacles",
            board=multi_board,
            routing_plan=multi_plan,
        )
    )

    return all_results


def save_json_results(
    results: list[dict[str, Any]],
) -> Path:
    """
    保存 JSON 实验结果。
    """

    output_path = (
        PROJECT_ROOT
        / "experiment"
        / "results"
        / "router_evaluation.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    document = {
        "metadata": {
            "experiment": (
                "LLM-PCB Router Evaluation"
            ),
            "version": "1.0",
        },
        "results": results,
    }

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            document,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path


def save_csv_results(
    results: list[dict[str, Any]],
) -> Path:
    """
    保存 CSV 实验结果，便于论文制表。
    """

    output_path = (
        PROJECT_ROOT
        / "experiment"
        / "results"
        / "router_evaluation.csv"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    field_names = [
        "scenario",
        "router",
        "success",
        "collision_count",
        "total_length_mm",
        "segment_count",
        "bend_count",
        "runtime_ms",
        "error",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=field_names,
        )

        writer.writeheader()
        writer.writerows(results)

    return output_path


def print_results(
    results: list[dict[str, Any]],
) -> None:
    """
    在终端打印易读的结果表。
    """

    print("=" * 105)
    print("ROUTER EVALUATION RESULTS")
    print("=" * 105)

    header = (
        f"{'Scenario':<22}"
        f"{'Router':<28}"
        f"{'Success':<10}"
        f"{'Collision':<12}"
        f"{'Length':<12}"
        f"{'Bends':<8}"
        f"{'Runtime(ms)':<12}"
    )

    print(header)
    print("-" * 105)

    for result in results:
        collision = result[
            "collision_count"
        ]

        length = result[
            "total_length_mm"
        ]

        bends = result[
            "bend_count"
        ]

        print(
            f"{result['scenario']:<22}"
            f"{result['router']:<28}"
            f"{str(result['success']):<10}"
            f"{str(collision):<12}"
            f"{str(length):<12}"
            f"{str(bends):<8}"
            f"{result['runtime_ms']:<12}"
        )

        if result["error"]:
            print(
                "  Error: "
                f"{result['error']}"
            )


def validate_results(
    results: list[dict[str, Any]],
) -> None:
    """
    严格检查统一评估结果。
    """

    single_results = {
        result["router"]: result
        for result in results
        if result["scenario"] == "Single Obstacle"
    }

    naive = single_results[
        "Naive Manhattan"
    ]

    detour = single_results[
        "Obstacle-Aware Manhattan"
    ]

    astar = single_results[
        "Grid A*"
    ]

    assert naive["success"] is True
    assert naive["collision_count"] > 0

    assert detour["success"] is True
    assert detour["collision_count"] == 0

    assert astar["success"] is True, (
        "Grid A* failed in Single Obstacle: "
        f"{astar['error']}"
    )

    assert astar["collision_count"] == 0, (
        "Grid A* generated a colliding route."
    )

    print(
        "\nRouter evaluation validation passed."
    )


if __name__ == "__main__":
    evaluation_results = run_evaluation()

    print_results(evaluation_results)

    validate_results(evaluation_results)

    json_path = save_json_results(
        evaluation_results
    )

    csv_path = save_csv_results(
        evaluation_results
    )

    print(f"\nJSON results: {json_path}")
    print(f"CSV results: {csv_path}")