from src.pcb.obstacle import PCBObstacle
from src.pcb.obstacle_detector import ObstacleDetector
from src.pcb.route import RoutePoint, RouteSegment


class DetourRouter:
    """
    为发生障碍物碰撞的曼哈顿路径生成候选绕障路径。
    """

    def __init__(
        self,
        clearance: float = 2.0,
    ) -> None:
        if clearance < 0:
            raise ValueError(
                "Clearance cannot be negative."
            )

        self.clearance = clearance
        self.detector = ObstacleDetector()

    def generate_candidates(
        self,
        source: RoutePoint,
        target: RoutePoint,
        obstacle: PCBObstacle,
        width: float,
        layer: str,
    ) -> list[list[RoutePoint]]:
        """
        根据起点、终点和单个障碍物生成候选路径。
        """

        if source.y == target.y:
            return self._generate_horizontal_detours(
                source=source,
                target=target,
                obstacle=obstacle,
                width=width,
            )

        if source.x == target.x:
            return self._generate_vertical_detours(
                source=source,
                target=target,
                obstacle=obstacle,
                width=width,
            )

        raise ValueError(
            "Detour generation currently supports "
            "only horizontal or vertical direct paths."
        )

    def select_best_candidate(
        self,
        candidates: list[list[RoutePoint]],
        obstacles: list[PCBObstacle],
        width: float,
        layer: str,
        ignored_references: set[str] | None = None,
    ) -> list[RoutePoint]:
        """
        从全部候选路径中选择最短且无碰撞的一条。
        """

        valid_candidates = []

        for points in candidates:
            segments = self.build_segments(
                points=points,
                width=width,
                layer=layer,
            )

            if self._route_has_collision(
                segments=segments,
                obstacles=obstacles,
                ignored_references=ignored_references,
            ):
                continue

            total_length = sum(
                segment.length()
                for segment in segments
            )

            valid_candidates.append(
                (
                    total_length,
                    points,
                )
            )

        if not valid_candidates:
            raise RuntimeError(
                "No collision-free detour candidate found."
            )

        valid_candidates.sort(
            key=lambda item: item[0]
        )

        return valid_candidates[0][1]

    @staticmethod
    def build_segments(
        points: list[RoutePoint],
        width: float,
        layer: str,
    ) -> list[RouteSegment]:
        """
        把候选路径点转换为线段。
        """

        segments = []

        for index in range(len(points) - 1):
            start = points[index]
            end = points[index + 1]

            if (
                start.x == end.x
                and start.y == end.y
            ):
                continue

            segment = RouteSegment(
                start=start,
                end=end,
                width=width,
                layer=layer,
            )

            if not (
                segment.is_horizontal()
                or segment.is_vertical()
            ):
                raise ValueError(
                    "Detour segment must be "
                    "horizontal or vertical."
                )

            segments.append(segment)

        return segments

    def _generate_horizontal_detours(
        self,
        source: RoutePoint,
        target: RoutePoint,
        obstacle: PCBObstacle,
        width: float,
    ) -> list[list[RoutePoint]]:
        """
        为水平直线路径生成上绕和下绕候选。
        """

        margin = (
            self.clearance
            + width / 2
        )

        upper_y = (
            obstacle.rectangle.top
            + margin
        )

        lower_y = (
            obstacle.rectangle.bottom
            - margin
        )

        upper_candidate = [
            source,
            RoutePoint(
                x=source.x,
                y=upper_y,
            ),
            RoutePoint(
                x=target.x,
                y=upper_y,
            ),
            target,
        ]

        lower_candidate = [
            source,
            RoutePoint(
                x=source.x,
                y=lower_y,
            ),
            RoutePoint(
                x=target.x,
                y=lower_y,
            ),
            target,
        ]

        return [
            upper_candidate,
            lower_candidate,
        ]

    def _generate_vertical_detours(
        self,
        source: RoutePoint,
        target: RoutePoint,
        obstacle: PCBObstacle,
        width: float,
    ) -> list[list[RoutePoint]]:
        """
        为垂直直线路径生成左绕和右绕候选。
        """

        margin = (
            self.clearance
            + width / 2
        )

        left_x = (
            obstacle.rectangle.left
            - margin
        )

        right_x = (
            obstacle.rectangle.right
            + margin
        )

        left_candidate = [
            source,
            RoutePoint(
                x=left_x,
                y=source.y,
            ),
            RoutePoint(
                x=left_x,
                y=target.y,
            ),
            target,
        ]

        right_candidate = [
            source,
            RoutePoint(
                x=right_x,
                y=source.y,
            ),
            RoutePoint(
                x=right_x,
                y=target.y,
            ),
            target,
        ]

        return [
            left_candidate,
            right_candidate,
        ]

    def _route_has_collision(
        self,
        segments: list[RouteSegment],
        obstacles: list[PCBObstacle],
        ignored_references: set[str] | None,
    ) -> bool:
        """
        判断整条候选路径是否与任意障碍物碰撞。
        """

        for segment in segments:
            collisions = self.detector.find_collisions(
                segment=segment,
                obstacles=obstacles,
                ignored_references=ignored_references,
            )

            if collisions:
                return True

        return False