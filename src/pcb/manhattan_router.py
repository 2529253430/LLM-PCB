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

    def route(
        self,
        routing_plan: RoutingPlan,
    ) -> RoutingResult:
        """
        对全部网络进行几何布线。
        """

        routing_result = RoutingResult()

        for net_plan in (
            routing_plan.get_sorted_plans()
        ):
            routed_net = self._route_net(
                net_plan
            )

            routing_result.add_routed_net(
                routed_net
            )

        return routing_result

    def _route_net(
        self,
        net_plan: NetRoutingPlan,
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
                )
            )

            routed_net.add_connection(connection)

        return routed_net

    def _route_connection(
        self,
        source: RoutingEndpoint,
        target: RoutingEndpoint,
        net_plan: NetRoutingPlan,
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