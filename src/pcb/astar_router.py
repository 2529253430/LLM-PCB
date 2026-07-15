from __future__ import annotations

import heapq
from dataclasses import dataclass

from src.pcb.board import PCBBoard
from src.pcb.obstacle import PCBObstacle
from src.pcb.obstacle_detector import ObstacleDetector
from src.pcb.route import (
    RoutedConnection,
    RoutedNet,
    RoutePoint,
    RouteSegment,
    RoutingResult,
)
from src.pcb.routing_plan import (
    NetRoutingPlan,
    RoutingEndpoint,
    RoutingPlan,
)


@dataclass(frozen=True)
class GridNode:
    """
    A* 搜索使用的整数网格节点。
    """

    x_index: int
    y_index: int


class AStarGridRouter:
    """
    基于二维正交网格的 A* PCB 路由器。

    当前版本：
    - 只允许上下左右移动；
    - 每次移动一个网格；
    - 不使用过孔；
    - 每条连接独立搜索；
    - 元件矩形作为障碍物；
    - 暂不把已有走线作为障碍物。
    """

    def __init__(
        self,
        grid_size: float = 2.0,
        obstacle_clearance: float = 1.0,
    ) -> None:
        if grid_size <= 0:
            raise ValueError(
                "Grid size must be greater than 0."
            )

        if obstacle_clearance < 0:
            raise ValueError(
                "Obstacle clearance cannot be negative."
            )

        self.grid_size = grid_size
        self.obstacle_clearance = obstacle_clearance
        self.detector = ObstacleDetector()

    def route(
        self,
        routing_plan: RoutingPlan,
        board: PCBBoard,
    ) -> RoutingResult:
        """
        对 RoutingPlan 中的全部网络执行 A* 搜索。
        """

        routing_result = RoutingResult()

        obstacles = board.build_component_obstacles(
            clearance=self.obstacle_clearance
        )

        for net_plan in routing_plan.get_sorted_plans():
            routed_net = self._route_net(
                net_plan=net_plan,
                board=board,
                obstacles=obstacles,
            )

            routing_result.add_routed_net(
                routed_net
            )

        return routing_result

    def _route_net(
        self,
        net_plan: NetRoutingPlan,
        board: PCBBoard,
        obstacles: list[PCBObstacle],
    ) -> RoutedNet:
        """
        多端点网络继续采用星形连接：
        第一个端点分别连接其余端点。
        """

        routed_net = RoutedNet(
            net_name=net_plan.net_name,
            priority=net_plan.priority,
            preferred_width=(
                net_plan.preferred_width
            ),
            preferred_layer=(
                net_plan.preferred_layer
            ),
        )

        if len(net_plan.endpoints) < 2:
            return routed_net

        source = net_plan.endpoints[0]

        for target in net_plan.endpoints[1:]:
            connection = self._route_connection(
                source=source,
                target=target,
                net_plan=net_plan,
                board=board,
                obstacles=obstacles,
            )

            routed_net.add_connection(connection)

        return routed_net

    def _route_connection(
        self,
        source: RoutingEndpoint,
        target: RoutingEndpoint,
        net_plan: NetRoutingPlan,
        board: PCBBoard,
        obstacles: list[PCBObstacle],
    ) -> RoutedConnection:
        """
        对两个端点执行一次 A* 搜索。
        """

        source_point = RoutePoint(
            source.x,
            source.y,
        )

        target_point = RoutePoint(
            target.x,
            target.y,
        )

        ignored_references = {
            source.reference,
            target.reference,
        }

        grid_path = self._search(
            source=source_point,
            target=target_point,
            board=board,
            obstacles=obstacles,
            ignored_references=ignored_references,
            trace_width=net_plan.preferred_width,
        )

        route_points = [
            self._grid_to_point(node)
            for node in grid_path
        ]

        # 保留真实起点和终点，避免网格取整后发生偏移。
        route_points[0] = source_point
        route_points[-1] = target_point

        route_points = self._compress_points(
            route_points
        )

        segments = self._build_segments(
            points=route_points,
            width=net_plan.preferred_width,
            layer=net_plan.preferred_layer,
        )

        return RoutedConnection(
            source_reference=source.reference,
            source_pin=source.pin_number,
            target_reference=target.reference,
            target_pin=target.pin_number,
            points=route_points,
            segments=segments,
        )

    def _search(
        self,
        source: RoutePoint,
        target: RoutePoint,
        board: PCBBoard,
        obstacles: list[PCBObstacle],
        ignored_references: set[str],
        trace_width: float,
    ) -> list[GridNode]:
        """
        执行标准 A* 网格搜索。
        """

        start = self._point_to_grid(source)
        goal = self._point_to_grid(target)

        open_heap: list[
            tuple[float, int, GridNode]
        ] = []

        sequence_number = 0

        heapq.heappush(
            open_heap,
            (
                0.0,
                sequence_number,
                start,
            ),
        )

        came_from: dict[
            GridNode,
            GridNode,
        ] = {}

        g_score: dict[
            GridNode,
            float,
        ] = {
            start: 0.0
        }

        closed_set: set[GridNode] = set()

        while open_heap:
            _, _, current = heapq.heappop(
                open_heap
            )

            if current in closed_set:
                continue

            if current == goal:
                return self._reconstruct_path(
                    came_from=came_from,
                    current=current,
                )

            closed_set.add(current)

            for neighbor in self._neighbors(current):
                if neighbor in closed_set:
                    continue

                if not self._grid_node_inside_board(
                    node=neighbor,
                    board=board,
                ):
                    continue

                if (
                    neighbor != goal
                    and neighbor != start
                    and self._grid_node_is_blocked(
                        node=neighbor,
                        obstacles=obstacles,
                        ignored_references=(
                            ignored_references
                        ),
                        trace_width=trace_width,
                    )
                ):
                    continue

                tentative_score = (
                    g_score[current] + 1.0
                )

                if tentative_score >= g_score.get(
                    neighbor,
                    float("inf"),
                ):
                    continue

                came_from[neighbor] = current
                g_score[neighbor] = (
                    tentative_score
                )

                estimated_total = (
                    tentative_score
                    + self._heuristic(
                        neighbor,
                        goal,
                    )
                )

                sequence_number += 1

                heapq.heappush(
                    open_heap,
                    (
                        estimated_total,
                        sequence_number,
                        neighbor,
                    ),
                )

        raise RuntimeError(
            "A* could not find a collision-free path."
        )

    @staticmethod
    def _neighbors(
        node: GridNode,
    ) -> list[GridNode]:
        """
        仅允许四方向正交移动。
        """

        return [
            GridNode(
                node.x_index + 1,
                node.y_index,
            ),
            GridNode(
                node.x_index - 1,
                node.y_index,
            ),
            GridNode(
                node.x_index,
                node.y_index + 1,
            ),
            GridNode(
                node.x_index,
                node.y_index - 1,
            ),
        ]

    @staticmethod
    def _heuristic(
        first: GridNode,
        second: GridNode,
    ) -> float:
        """
        曼哈顿距离启发函数。
        """

        return float(
            abs(
                first.x_index
                - second.x_index
            )
            + abs(
                first.y_index
                - second.y_index
            )
        )

    def _point_to_grid(
        self,
        point: RoutePoint,
    ) -> GridNode:
        return GridNode(
            x_index=round(
                point.x / self.grid_size
            ),
            y_index=round(
                point.y / self.grid_size
            ),
        )

    def _grid_to_point(
        self,
        node: GridNode,
    ) -> RoutePoint:
        return RoutePoint(
            x=node.x_index * self.grid_size,
            y=node.y_index * self.grid_size,
        )

    def _grid_node_inside_board(
        self,
        node: GridNode,
        board: PCBBoard,
    ) -> bool:
        point = self._grid_to_point(node)

        return (
            0 <= point.x <= board.width
            and 0 <= point.y <= board.height
        )

    def _grid_node_is_blocked(
        self,
        node: GridNode,
        obstacles: list[PCBObstacle],
        ignored_references: set[str],
        trace_width: float,
    ) -> bool:
        """
        判断网格点是否位于扩展后的障碍区域中。
        """

        point = self._grid_to_point(node)

        expansion = trace_width / 2

        for obstacle in obstacles:
            if (
                obstacle.reference
                in ignored_references
            ):
                continue

            rectangle = obstacle.rectangle

            if (
                rectangle.left - expansion
                <= point.x
                <= rectangle.right + expansion
                and rectangle.bottom - expansion
                <= point.y
                <= rectangle.top + expansion
            ):
                return True

        return False

    @staticmethod
    def _reconstruct_path(
        came_from: dict[
            GridNode,
            GridNode,
        ],
        current: GridNode,
    ) -> list[GridNode]:
        path = [current]

        while current in came_from:
            current = came_from[current]
            path.append(current)

        path.reverse()

        return path

    @staticmethod
    def _compress_points(
        points: list[RoutePoint],
    ) -> list[RoutePoint]:
        """
        删除同一直线上的中间网格点。

        例如：
        (0,0),(2,0),(4,0),(4,2)
        压缩为：
        (0,0),(4,0),(4,2)
        """

        if len(points) <= 2:
            return points

        compressed = [points[0]]

        for index in range(
            1,
            len(points) - 1,
        ):
            previous = compressed[-1]
            current = points[index]
            following = points[index + 1]

            same_horizontal = (
                previous.y == current.y
                == following.y
            )

            same_vertical = (
                previous.x == current.x
                == following.x
            )

            if (
                same_horizontal
                or same_vertical
            ):
                continue

            compressed.append(current)

        compressed.append(points[-1])

        return compressed

    @staticmethod
    def _build_segments(
        points: list[RoutePoint],
        width: float,
        layer: str,
    ) -> list[RouteSegment]:
        segments = []

        for index in range(
            len(points) - 1
        ):
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
                    "A* output contains a "
                    "non-Manhattan segment."
                )

            segments.append(segment)

        return segments