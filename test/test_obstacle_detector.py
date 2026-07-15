from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))

from src.pcb.obstacle import (
    PCBObstacle,
    Rectangle,
)
from src.pcb.obstacle_detector import (
    ObstacleDetector,
)
from src.pcb.route import (
    RoutePoint,
    RouteSegment,
)
from test_placement_pipeline import (
    build_test_placement,
)


def test_horizontal_collision() -> None:
    detector = ObstacleDetector()

    obstacle = PCBObstacle(
        reference="C1",
        obstacle_type="Component",
        rectangle=Rectangle(
            left=40,
            right=50,
            bottom=35,
            top=45,
        ),
    )

    colliding_segment = RouteSegment(
        start=RoutePoint(30, 40),
        end=RoutePoint(60, 40),
        width=1.0,
        layer="Top",
    )

    safe_segment = RouteSegment(
        start=RoutePoint(30, 50),
        end=RoutePoint(60, 50),
        width=1.0,
        layer="Top",
    )

    assert detector.segment_intersects_obstacle(
        colliding_segment,
        obstacle,
    )

    assert not detector.segment_intersects_obstacle(
        safe_segment,
        obstacle,
    )

    print(
        "Horizontal collision detection passed."
    )


def test_vertical_collision() -> None:
    detector = ObstacleDetector()

    obstacle = PCBObstacle(
        reference="C1",
        obstacle_type="Component",
        rectangle=Rectangle(
            left=40,
            right=50,
            bottom=35,
            top=45,
        ),
    )

    colliding_segment = RouteSegment(
        start=RoutePoint(45, 20),
        end=RoutePoint(45, 60),
        width=1.0,
        layer="Top",
    )

    safe_segment = RouteSegment(
        start=RoutePoint(60, 20),
        end=RoutePoint(60, 60),
        width=1.0,
        layer="Top",
    )

    assert detector.segment_intersects_obstacle(
        colliding_segment,
        obstacle,
    )

    assert not detector.segment_intersects_obstacle(
        safe_segment,
        obstacle,
    )

    print(
        "Vertical collision detection passed."
    )


def test_board_obstacles() -> None:
    board = build_test_placement()

    obstacles = (
        board.build_component_obstacles(
            clearance=1.0
        )
    )

    assert len(obstacles) == 6

    references = {
        obstacle.reference
        for obstacle in obstacles
    }

    assert references == {
        "U1",
        "CIN",
        "L1",
        "COUT",
        "R1",
        "R2",
    }

    print(
        "Board obstacle generation passed."
    )


def test_existing_sw_route() -> None:
    """
    检查 U1 到 L1 的 SW 路径。

    起点与终点元件应被忽略。
    """

    board = build_test_placement()

    obstacles = board.build_component_obstacles(
        clearance=0.5
    )

    detector = ObstacleDetector()

    segment = RouteSegment(
        start=RoutePoint(32, 40),
        end=RoutePoint(52, 40),
        width=2.0,
        layer="Top",
    )

    collisions = detector.find_collisions(
        segment=segment,
        obstacles=obstacles,
        ignored_references={
            "U1",
            "L1",
        },
    )

    print(
        "SW route collisions:",
        [
            obstacle.reference
            for obstacle in collisions
        ],
    )

def test_route_through_component() -> None:
    """
    构造一条穿过 U1 的测试线路。
    """

    board = build_test_placement()

    obstacles = board.build_component_obstacles(
        clearance=0.5
    )

    detector = ObstacleDetector()

    segment = RouteSegment(
        start=RoutePoint(10, 40),
        end=RoutePoint(60, 40),
        width=1.0,
        layer="Top",
    )

    collisions = detector.find_collisions(
        segment=segment,
        obstacles=obstacles,
    )

    collision_references = [
        obstacle.reference
        for obstacle in collisions
    ]

    print(
        "Long route collisions:",
        collision_references,
    )

    assert "CIN" in collision_references
    assert "U1" in collision_references
    assert "L1" in collision_references

    print(
        "Route-through-component detection passed."
    )

if __name__ == "__main__":
    print("=" * 60)
    print("OBSTACLE DETECTOR TEST")
    print("=" * 60)

    test_horizontal_collision()
    test_vertical_collision()
    test_board_obstacles()
    test_existing_sw_route()
    test_route_through_component()

    print(
        "Obstacle detector validation passed."
    )