from src.constraint.constraint_graph import (
    ConstraintGraph,
)
from src.pcb.board import PCBBoard
from src.pcb.routing_plan import (
    NetRoutingPlan,
    RoutingEndpoint,
    RoutingPlan,
)
from src.schematic.circuit_graph import (
    CircuitGraph,
)


class ConstraintAwareRoutingPlanner:
    """
    根据电路连接、PCB坐标和规则生成布线计划。
    """

    NET_CONFIGURATION = {
        "SW": {
            "priority": 1,
            "width": 2.0,
            "layer": "Top",
            "avoid_nets": ["FB"],
        },
        "VIN": {
            "priority": 2,
            "width": 2.0,
            "layer": "Top",
            "avoid_nets": [],
        },
        "VOUT": {
            "priority": 3,
            "width": 1.5,
            "layer": "Top",
            "avoid_nets": [],
        },
        "FB": {
            "priority": 4,
            "width": 0.3,
            "layer": "Top",
            "avoid_nets": ["SW"],
        },
        "GND": {
            "priority": 5,
            "width": 1.5,
            "layer": "Bottom",
            "avoid_nets": [],
        },
    }

    def create_plan(
        self,
        circuit_graph: CircuitGraph,
        constraint_graph: ConstraintGraph,
        board: PCBBoard,
    ) -> RoutingPlan:
        """
        为全部电气网络生成布线计划。
        """

        routing_plan = RoutingPlan()

        routing_rules = (
            self._extract_routing_rules(
                constraint_graph
            )
        )

        for _, net_data in (
            circuit_graph.get_nets()
        ):
            net_name = str(
                net_data["name"]
            )

            connections = (
                circuit_graph.get_net_connections(
                    net_name
                )
            )

            endpoints = (
                self._build_endpoints(
                    connections=connections,
                    board=board,
                )
            )

            configuration = (
                self._get_net_configuration(
                    net_name
                )
            )

            plan = NetRoutingPlan(
                net_name=net_name,
                endpoints=endpoints,
                priority=configuration[
                    "priority"
                ],
                preferred_width=configuration[
                    "width"
                ],
                strategy=(
                    self._select_strategy(
                        endpoints
                    )
                ),
                preferred_layer=configuration[
                    "layer"
                ],
                avoid_nets=list(
                    configuration[
                        "avoid_nets"
                    ]
                ),
                rule_texts=(
                    routing_rules.get(
                        net_name,
                        [],
                    )
                ),
            )

            routing_plan.add_net_plan(plan)

        return routing_plan

    @staticmethod
    def _extract_routing_rules(
        constraint_graph: ConstraintGraph,
    ) -> dict[str, list[str]]:
        """
        从 Constraint Graph 中读取布线规则。
        """

        rules_by_net: dict[
            str,
            list[str],
        ] = {}

        for _, data in (
            constraint_graph.graph.nodes(
                data=True
            )
        ):
            if (
                data.get("node_type")
                != "RoutingRule"
            ):
                continue

            net_name = str(
                data.get("net", "")
            )

            rule_text = str(
                data.get("rule", "")
            )

            if not net_name:
                continue

            rules_by_net.setdefault(
                net_name,
                [],
            ).append(rule_text)

        return rules_by_net

    @staticmethod
    def _build_endpoints(
        connections: list[dict[str, str]],
        board: PCBBoard,
    ) -> list[RoutingEndpoint]:
        """
        根据元件中心坐标建立第一版端点。

        当前尚未使用真实焊盘偏移，因此端点暂时
        使用元件中心坐标。
        """

        endpoints = []

        for connection in connections:
            reference = connection[
                "reference"
            ]

            placed_component = (
                board.get_component(reference)
            )

            endpoints.append(
                RoutingEndpoint(
                    reference=reference,
                    pin_number=connection[
                        "pin_number"
                    ],
                    pin_name=connection[
                        "pin_name"
                    ],
                    x=placed_component.x,
                    y=placed_component.y,
                )
            )

        return endpoints

    @classmethod
    def _get_net_configuration(
        cls,
        net_name: str,
    ) -> dict:
        """
        读取网络默认配置。
        """

        default_configuration = {
            "priority": 99,
            "width": 0.3,
            "layer": "Top",
            "avoid_nets": [],
        }

        return cls.NET_CONFIGURATION.get(
            net_name,
            default_configuration,
        )

    @staticmethod
    def _select_strategy(
        endpoints: list[RoutingEndpoint],
    ) -> str:
        """
        根据端点整体跨度选择初始布线策略。

        水平跨度较大：Horizontal First
        垂直跨度较大：Vertical First
        """

        if len(endpoints) < 2:
            return "Direct"

        x_values = [
            endpoint.x
            for endpoint in endpoints
        ]

        y_values = [
            endpoint.y
            for endpoint in endpoints
        ]

        horizontal_span = (
            max(x_values) - min(x_values)
        )

        vertical_span = (
            max(y_values) - min(y_values)
        )

        if horizontal_span >= vertical_span:
            return "Horizontal First"

        return "Vertical First"