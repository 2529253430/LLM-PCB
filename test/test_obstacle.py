from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pcb.obstacle import Rectangle, PCBObstacle


def test_rectangle():

    rect = Rectangle(
        left=10,
        right=20,
        bottom=30,
        top=40,
    )

    print(rect.to_dict())

    print(
        "Contains (15,35):",
        rect.contains_point(15, 35),
    )

    print(
        "Contains (25,35):",
        rect.contains_point(25, 35),
    )


def test_intersection():

    r1 = Rectangle(
        0,
        10,
        0,
        10,
    )

    r2 = Rectangle(
        8,
        20,
        5,
        15,
    )

    r3 = Rectangle(
        15,
        25,
        15,
        25,
    )

    print(
        "r1 intersects r2:",
        r1.intersects(r2),
    )

    print(
        "r1 intersects r3:",
        r1.intersects(r3),
    )


def test_obstacle():

    obstacle = PCBObstacle(
        reference="U1",
        obstacle_type="Component",
        rectangle=Rectangle(
            26,
            38,
            35,
            45,
        ),
    )

    print(obstacle.to_dict())


if __name__ == "__main__":

    print("=" * 60)
    print("RECTANGLE TEST")
    print("=" * 60)

    test_rectangle()

    print()

    print("=" * 60)
    print("INTERSECTION TEST")
    print("=" * 60)

    test_intersection()

    print()

    print("=" * 60)
    print("OBSTACLE TEST")
    print("=" * 60)

    test_obstacle()