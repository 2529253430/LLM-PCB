from src.pcb.obstacle import (
    PCBObstacle,
    Rectangle,
)
from src.pcb.route import RouteSegment


class ObstacleDetector:
    """
    检测走线线段是否与 PCB 障碍物发生碰撞。
    """

    def segment_intersects_obstacle(
        self,
        segment: RouteSegment,
        obstacle: PCBObstacle,
    ) -> bool:
        """
        判断一条水平或垂直线段是否穿过障碍物。

        当前把走线宽度也考虑进去。
        """

        expanded_rectangle = self._expand_rectangle(
            rectangle=obstacle.rectangle,
            margin=segment.width / 2,
        )

        if segment.is_horizontal():
            return self._horizontal_segment_intersects_rectangle(
                segment=segment,
                rectangle=expanded_rectangle,
            )

        if segment.is_vertical():
            return self._vertical_segment_intersects_rectangle(
                segment=segment,
                rectangle=expanded_rectangle,
            )

        raise ValueError(
            "Only horizontal or vertical segments "
            "are supported."
        )

    def find_collisions(
        self,
        segment: RouteSegment,
        obstacles: list[PCBObstacle],
        ignored_references: set[str] | None = None,
    ) -> list[PCBObstacle]:
        """
        返回与当前线段碰撞的全部障碍物。

        ignored_references:
            用于忽略起点和终点所属元件。
        """

        ignored_references = (
            ignored_references or set()
        )

        collisions = []

        for obstacle in obstacles:
            if obstacle.reference in ignored_references:
                continue

            if self.segment_intersects_obstacle(
                segment=segment,
                obstacle=obstacle,
            ):
                collisions.append(obstacle)

        return collisions

    @staticmethod
    def _expand_rectangle(
        rectangle: Rectangle,
        margin: float,
    ) -> Rectangle:
        """
        根据走线半宽扩展障碍物边界。
        """

        return Rectangle(
            left=rectangle.left - margin,
            right=rectangle.right + margin,
            bottom=rectangle.bottom - margin,
            top=rectangle.top + margin,
        )

    @staticmethod
    def _horizontal_segment_intersects_rectangle(
        segment: RouteSegment,
        rectangle: Rectangle,
    ) -> bool:
        """
        检测水平线段与矩形是否相交。
        """

        y = segment.start.y

        if not (
            rectangle.bottom
            <= y
            <= rectangle.top
        ):
            return False

        segment_left = min(
            segment.start.x,
            segment.end.x,
        )
        segment_right = max(
            segment.start.x,
            segment.end.x,
        )

        separated = (
            segment_right <= rectangle.left
            or segment_left >= rectangle.right
        )

        return not separated

    @staticmethod
    def _vertical_segment_intersects_rectangle(
        segment: RouteSegment,
        rectangle: Rectangle,
    ) -> bool:
        """
        检测垂直线段与矩形是否相交。
        """

        x = segment.start.x

        if not (
            rectangle.left
            <= x
            <= rectangle.right
        ):
            return False

        segment_bottom = min(
            segment.start.y,
            segment.end.y,
        )
        segment_top = max(
            segment.start.y,
            segment.end.y,
        )

        separated = (
            segment_top <= rectangle.bottom
            or segment_bottom >= rectangle.top
        )

        return not separated