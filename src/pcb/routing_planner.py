from __future__ import annotations

from src.constraint.constraint_graph import (
    ConstraintGraph,
)
from src.database.component_instance import (
    ComponentInstance,
)
from src.pcb.board import (
    PCBBoard,
    PlacedComponent,
)
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
    根据电路连接、PCB 坐标和规则生成布线计划。
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

        routing_rules = self._extract_routing_rules(
            constraint_graph
        )

        for _, net_data in circuit_graph.get_nets():
            net_name = str(
                net_data["name"]
            )

            connections = (
                circuit_graph.get_net_connections(
                    net_name
                )
            )

            endpoints = self._build_endpoints(
                connections=connections,
                board=board,
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
                strategy=self._select_strategy(
                    endpoints
                ),
                preferred_layer=configuration[
                    "layer"
                ],
                avoid_nets=list(
                    configuration[
                        "avoid_nets"
                    ]
                ),
                rule_texts=routing_rules.get(
                    net_name,
                    [],
                ),
            )

            routing_plan.add_net_plan(
                plan
            )

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
            ).strip()

            rule_text = str(
                data.get("rule", "")
            ).strip()

            if not net_name:
                continue

            if not rule_text:
                continue

            rules_by_net.setdefault(
                net_name,
                [],
            ).append(
                rule_text
            )

        return rules_by_net

    @staticmethod
    def _build_endpoints(
        connections: list[
            dict[str, str]
        ],
        board: PCBBoard,
    ) -> list[RoutingEndpoint]:
        """
        根据真实 Pad 坐标建立布线端点。

        有真实器件型号的元件使用 ComponentInstance；
        其他两引脚无源器件暂时使用简化 Pad 坐标。
        """

        endpoints: list[
            RoutingEndpoint
        ] = []

        for connection in connections:
            reference = str(
                connection["reference"]
            )

            pin_number = str(
                connection["pin_number"]
            )

            pin_name = str(
                connection.get(
                    "pin_name",
                    "",
                )
            )

            placed_component = (
                board.get_component(
                    reference
                )
            )

            if placed_component.part_number:
                instance = ComponentInstance(
                    reference=reference,
                    part_number=(
                        placed_component.part_number
                    ),
                    x=placed_component.x,
                    y=placed_component.y,
                    rotation=(
                        placed_component.rotation
                    ),
                )

                pad_position = (
                    instance.get_pad_position(
                        pin_number
                    )
                )

                endpoint_x = (
                    pad_position.x
                )

                endpoint_y = (
                    pad_position.y
                )
            else:
                (
                    endpoint_x,
                    endpoint_y,
                ) = (
                    ConstraintAwareRoutingPlanner
                    ._get_simplified_passive_pad_position(
                        placed_component=(
                            placed_component
                        ),
                        pin_number=pin_number,
                    )
                )

            endpoints.append(
                RoutingEndpoint(
                    reference=reference,
                    pin_number=pin_number,
                    pin_name=pin_name,
                    x=endpoint_x,
                    y=endpoint_y,
                )
            )

        return endpoints

    @staticmethod
    def _get_simplified_passive_pad_position(
        placed_component: PlacedComponent,
        pin_number: str,
    ) -> tuple[float, float]:
        """
        为尚未建立真实封装库的两引脚无源器件
        生成简化 Pad 坐标。

        当前约定：
        - Pin 1 位于元件左侧；
        - Pin 2 位于元件右侧。

        旋转为 90° 或 270° 时，焊盘改为上下分布。
        """

        normalized_pin = str(
            pin_number
        ).strip()

        half_width = (
            placed_component.width / 2
        )

        half_height = (
            placed_component.height / 2
        )

        rotation = (
            placed_component.rotation
            % 360.0
        )

        if rotation in (
            90.0,
            270.0,
        ):
            if normalized_pin == "1":
                return (
                    placed_component.x,
                    placed_component.y
                    - half_height,
                )

            if normalized_pin == "2":
                return (
                    placed_component.x,
                    placed_component.y
                    + half_height,
                )

        else:
            if normalized_pin == "1":
                return (
                    placed_component.x
                    - half_width,
                    placed_component.y,
                )

            if normalized_pin == "2":
                return (
                    placed_component.x
                    + half_width,
                    placed_component.y,
                )

        return (
            placed_component.x,
            placed_component.y,
        )

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
        endpoints: list[
            RoutingEndpoint
        ],
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
            max(x_values)
            - min(x_values)
        )

        vertical_span = (
            max(y_values)
            - min(y_values)
        )

        if horizontal_span >= vertical_span:
            return "Horizontal First"

        return "Vertical First"