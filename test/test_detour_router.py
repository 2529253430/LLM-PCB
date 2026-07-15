from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pcb.detour_router import DetourRouter
from src.pcb.obstacle import PCBObstacle, Rectangle
from src.pcb.route import RoutePoint


def format_points(
    points: list[RoutePoint],
) -> str:
    return " -> ".join(
        f"({point.x}, {point.y})"
        for point in points
    )


def test_horizontal_detour() -> None:
    router = DetourRouter(
        clearance=2.0
    )

    source = RoutePoint(
        x=10,
        y=40,
    )

    target = RoutePoint(
        x=60,
        y=40,
    )

    obstacle = PCBObstacle(
        reference="U1",
        obstacle_type="Component",
        rectangle=Rectangle(
            left=25,
            right=35,
            bottom=35,
            top=45,
        ),
    )

    candidates = router.generate_candidates(
        source=source,
        target=target,
        obstacle=obstacle,
        width=1.0,
        layer="Top",
    )

    assert len(candidates) == 2

    print("Horizontal candidates:")

    for candidate in candidates:
        print(
            "-",
            format_points(candidate),
        )

    best = router.select_best_candidate(
        candidates=candidates,
        obstacles=[obstacle],
        width=1.0,
        layer="Top",
    )

    print(
        "Best horizontal detour:",
        format_points(best),
    )

    assert len(best) == 4

    print(
        "Horizontal detour generation passed."
    )


def test_vertical_detour() -> None:
    router = DetourRouter(
        clearance=2.0
    )

    source = RoutePoint(
        x=45,
        y=10,
    )

    target = RoutePoint(
        x=45,
        y=70,
    )

    obstacle = PCBObstacle(
        reference="L1",
        obstacle_type="Component",
        rectangle=Rectangle(
            left=40,
            right=50,
            bottom=30,
            top=45,
        ),
    )

    candidates = router.generate_candidates(
        source=source,
        target=target,
        obstacle=obstacle,
        width=1.0,
        layer="Top",
    )

    assert len(candidates) == 2

    print("Vertical candidates:")

    for candidate in candidates:
        print(
            "-",
            format_points(candidate),
        )

    best = router.select_best_candidate(
        candidates=candidates,
        obstacles=[obstacle],
        width=1.0,
        layer="Top",
    )

    print(
        "Best vertical detour:",
        format_points(best),
    )

    assert len(best) == 4

    print(
        "Vertical detour generation passed."
    )


def test_second_obstacle_rejection() -> None:
    """
    验证某个候选方向被第二个障碍物挡住时，
    自动选择另一个方向。
    """

    router = DetourRouter(
        clearance=2.0
    )

    source = RoutePoint(
        x=10,
        y=40,
    )

    target = RoutePoint(
        x=60,
        y=40,
    )

    main_obstacle = PCBObstacle(
        reference="U1",
        obstacle_type="Component",
        rectangle=Rectangle(
            left=25,
            right=35,
            bottom=35,
            top=45,
        ),
    )

    upper_obstacle = PCBObstacle(
        reference="C1",
        obstacle_type="Component",
        rectangle=Rectangle(
            left=20,
            right=40,
            bottom=47,
            top=55,
        ),
    )

    candidates = router.generate_candidates(
        source=source,
        target=target,
        obstacle=main_obstacle,
        width=1.0,
        layer="Top",
    )

    best = router.select_best_candidate(
        candidates=candidates,
        obstacles=[
            main_obstacle,
            upper_obstacle,
        ],
        width=1.0,
        layer="Top",
    )

    best_y_values = {
        point.y
        for point in best
    }

    assert min(best_y_values) < 35

    print(
        "Blocked-candidate rejection passed."
    )


if __name__ == "__main__":
    print("=" * 60)
    print("DETOUR ROUTER TEST")
    print("=" * 60)

    test_horizontal_detour()
    print()

    test_vertical_detour()
    print()

    test_second_obstacle_rejection()

    print()
    print(
        "Detour router validation passed."
    )