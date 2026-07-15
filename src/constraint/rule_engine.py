from typing import Any

from src.constraint.constraint_graph import ConstraintGraph
from src.knowledge.knowledge_loader import (
    load_placement_rules,
    load_routing_rules,
)


class RuleEngine:
    """
    将 PCB 布局规则和布线规则加入 Constraint Graph。
    """

    def __init__(self) -> None:
        self.placement_rules = load_placement_rules()
        self.routing_rules = load_routing_rules()

    def apply_rules(
        self,
        graph: ConstraintGraph,
        topology_name: str,
    ) -> ConstraintGraph:
        """
        为指定拓扑注入全部布局和布线规则。
        """

        topology_node_id = f"topology_{topology_name.lower()}"

        if topology_node_id not in graph.graph:
            raise ValueError(
                f"Topology node does not exist: {topology_node_id}"
            )

        self._add_placement_rules(
            graph=graph,
            topology_name=topology_name,
            topology_node_id=topology_node_id,
        )

        self._add_routing_rules(
            graph=graph,
            topology_name=topology_name,
            topology_node_id=topology_node_id,
        )

        return graph

    def _add_placement_rules(
        self,
        graph: ConstraintGraph,
        topology_name: str,
        topology_node_id: str,
    ) -> None:
        """
        注入布局规则。
        """

        rules = self.placement_rules.get(topology_name, [])

        for index, rule_data in enumerate(rules, start=1):
            component_name = rule_data.get("component", "")
            rule_text = rule_data.get("rule", "")

            node_id = (
                f"placement_rule_{topology_name.lower()}_{index}"
            )

            graph.add_node(
                node_id=node_id,
                node_type="PlacementRule",
                name=f"{component_name} placement rule",
                component=component_name,
                rule=rule_text,
                topology=topology_name,
            )

            graph.add_edge(
                source=topology_node_id,
                target=node_id,
                relation="has_placement_rule",
            )

            self._connect_rule_to_component_type(
                graph=graph,
                rule_node_id=node_id,
                component_name=component_name,
            )

    def _add_routing_rules(
        self,
        graph: ConstraintGraph,
        topology_name: str,
        topology_node_id: str,
    ) -> None:
        """
        注入布线规则。
        """

        rules = self.routing_rules.get(topology_name, [])

        for index, rule_data in enumerate(rules, start=1):
            net_name = rule_data.get("net", "")
            rule_text = rule_data.get("rule", "")

            net_node_id = (
                f"net_{topology_name.lower()}_{net_name.lower()}"
            )

            if net_node_id not in graph.graph:
                graph.add_node(
                    node_id=net_node_id,
                    node_type="Net",
                    name=net_name,
                    topology=topology_name,
                )

                graph.add_edge(
                    source=topology_node_id,
                    target=net_node_id,
                    relation="contains_net",
                )

            rule_node_id = (
                f"routing_rule_{topology_name.lower()}_{index}"
            )

            graph.add_node(
                node_id=rule_node_id,
                node_type="RoutingRule",
                name=f"{net_name} routing rule",
                net=net_name,
                rule=rule_text,
                topology=topology_name,
            )

            graph.add_edge(
                source=topology_node_id,
                target=rule_node_id,
                relation="has_routing_rule",
            )

            graph.add_edge(
                source=net_node_id,
                target=rule_node_id,
                relation="governed_by",
            )

    @staticmethod
    def _connect_rule_to_component_type(
        graph: ConstraintGraph,
        rule_node_id: str,
        component_name: str,
    ) -> None:
        """
        尝试将布局规则连接到对应的必需器件类型节点。
        """

        normalized_name = component_name.strip().lower()

        for node_id, node_data in graph.graph.nodes(data=True):
            if node_data.get("node_type") != "RequiredComponentType":
                continue

            existing_name = str(
                node_data.get("name", "")
            ).strip().lower()

            if existing_name == normalized_name:
                graph.add_edge(
                    source=node_id,
                    target=rule_node_id,
                    relation="constrained_by",
                )
                return