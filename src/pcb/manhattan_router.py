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
from src.pcb.board import PCBBoard
from src.pcb.detour_router import DetourRouter
from src.pcb.obstacle_detector import ObstacleDetector

class ManhattanRouter:
    """
    将 RoutingPlan 转换成正交折线路径。

    当前版本：
    - 不使用过孔；
    - 不跨层切换；
    - 不考虑真实焊盘位置；
    - 使用元件中心作为布线端点；
    - 使用星形连接方式处理多端点网络。
    """
    def __init__(
        self,
        obstacle_clearance: float = 1.0,
        detour_clearance: float = 2.0,
    ) -> None:
        self.obstacle_clearance = (
            obstacle_clearance
        )
        self.detector = ObstacleDetector()
        self.detour_router = DetourRouter(
            clearance=detour_clearance
        )

    def route(
        self,
        routing_plan: RoutingPlan,
        board: PCBBoard | None = None,
    ) -> RoutingResult:
        """
        对全部网络进行几何布线。
        """
        obstacles = []

        if board is not None:
            obstacles = (
                board.build_component_obstacles(
                    clearance=(
                        self.obstacle_clearance
                    )
                )
            )

        routing_result = RoutingResult()

        for net_plan in (
            routing_plan.get_sorted_plans()
        ):
            routed_net = self._route_net(
                 net_plan=net_plan,
                 obstacles=obstacles,
            )

            routing_result.add_routed_net(
                routed_net
            )

        return routing_result



    def _route_net(
        self,
        net_plan: NetRoutingPlan,
         obstacles,
    ) -> RoutedNet:
        """
        布置一个网络。

        多端点网络采用：
        第一个端点作为主端点，
        依次连接其余端点。
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

        endpoints = net_plan.endpoints

        if len(endpoints) < 2:
            return routed_net

        source_endpoint = endpoints[0]

        for target_endpoint in endpoints[1:]:
            connection = (
                self._route_connection(
                    source=source_endpoint,
                    target=target_endpoint,
                    net_plan=net_plan,
                    obstacles=obstacles,
                )
            )

            routed_net.add_connection(connection)

        return routed_net

    def _route_connection(
        self,
        source: RoutingEndpoint,
        target: RoutingEndpoint,
        net_plan: NetRoutingPlan,
        obstacles,
    ) -> RoutedConnection:
        """
        根据 Routing Plan 中的策略生成折线路径。
        """

        source_point = RoutePoint(
            x=source.x,
            y=source.y,
        )

        target_point = RoutePoint(
            x=target.x,
            y=target.y,
        )

        points = self._build_points(
            source=source_point,
            target=target_point,
            strategy=net_plan.strategy,
        )

        segments = self._build_segments(
            points=points,
            width=net_plan.preferred_width,
            layer=net_plan.preferred_layer,
        )

        ignored_references = {
            source.reference,
            target.reference,
        }

        collision_obstacles = []

        for segment in segments:
            collision_obstacles.extend(
                self.detector.find_collisions(
                    segment=segment,
                    obstacles=obstacles,
                    ignored_references=(
                        ignored_references
                    ),
                )
            )

        if collision_obstacles:
            first_obstacle = (
                collision_obstacles[0]
            )

            if (
                source_point.x == target_point.x
                or source_point.y
                == target_point.y
            ):
                candidates = (
                    self.detour_router
                    .generate_candidates(
                        source=source_point,
                        target=target_point,
                        obstacle=first_obstacle,
                        width=(
                            net_plan
                            .preferred_width
                        ),
                        layer=(
                            net_plan
                            .preferred_layer
                        ),
                    )
                )

                points = (
                    self.detour_router
                    .select_best_candidate(
                        candidates=candidates,
                        obstacles=obstacles,
                        width=(
                            net_plan
                            .preferred_width
                        ),
                        layer=(
                            net_plan
                            .preferred_layer
                        ),
                        ignored_references=(
                            ignored_references
                        ),
                    )
                )

                segments = (
                    self.detour_router
                    .build_segments(
                        points=points,
                        width=(
                            net_plan
                            .preferred_width
                        ),
                        layer=(
                            net_plan
                            .preferred_layer
                        ),
                    )
                )

        return RoutedConnection(
            source_reference=source.reference,
            source_pin=source.pin_number,
            target_reference=target.reference,
            target_pin=target.pin_number,
            points=points,
            segments=segments,
        )

    @staticmethod
    def _build_points(
        source: RoutePoint,
        target: RoutePoint,
        strategy: str,
    ) -> list[RoutePoint]:
        """
        生成曼哈顿路径点。
        """

        if (
            source.x == target.x
            or source.y == target.y
        ):
            return [
                source,
                target,
            ]

        if strategy == "Vertical First":
            corner = RoutePoint(
                x=source.x,
                y=target.y,
            )
        else:
            corner = RoutePoint(
                x=target.x,
                y=source.y,
            )

        return [
            source,
            corner,
            target,
        ]

    @staticmethod
    def _build_segments(
        points: list[RoutePoint],
        width: float,
        layer: str,
    ) -> list[RouteSegment]:
        """
        把路径点转换成线段。
        """

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
                    "Manhattan segment must be "
                    "horizontal or vertical."
                )

            segments.append(segment)

        return segments