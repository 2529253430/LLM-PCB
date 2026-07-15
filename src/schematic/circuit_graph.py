from typing import Any

import networkx as nx


class CircuitGraph:
    """
    原理图电路图。

    图中包含三类节点：
    1. Component：元件
    2. Pin：引脚
    3. Net：电气网络
    """

    def __init__(self) -> None:
        self.graph = nx.Graph()

    def add_component(
        self,
        reference: str,
        component_type: str,
        part_number: str = "",
        value: str = "",
        **attributes: Any,
    ) -> None:
        """
        添加元件，例如 U1、L1、CIN。
        """

        if reference in self.graph:
            raise ValueError(
                f"Component already exists: {reference}"
            )

        self.graph.add_node(
            reference,
            node_type="Component",
            reference=reference,
            component_type=component_type,
            part_number=part_number,
            value=value,
            **attributes,
        )

    def add_pin(
        self,
        reference: str,
        pin_number: str,
        pin_name: str,
    ) -> str:
        """
        给元件添加引脚。

        返回引脚节点编号，例如：
        U1:VIN
        L1:1
        """

        if reference not in self.graph:
            raise ValueError(
                f"Component does not exist: {reference}"
            )

        pin_id = f"{reference}:{pin_number}"

        if pin_id in self.graph:
            raise ValueError(
                f"Pin already exists: {pin_id}"
            )

        self.graph.add_node(
            pin_id,
            node_type="Pin",
            reference=reference,
            pin_number=str(pin_number),
            pin_name=pin_name,
        )

        self.graph.add_edge(
            reference,
            pin_id,
            relation="has_pin",
        )

        return pin_id

    def add_net(self, net_name: str) -> str:
        """
        添加网络，例如 VIN、SW、VOUT、FB、GND。
        """

        net_id = f"net:{net_name}"

        if net_id not in self.graph:
            self.graph.add_node(
                net_id,
                node_type="Net",
                name=net_name,
            )

        return net_id

    def connect_pin(
        self,
        reference: str,
        pin_number: str,
        net_name: str,
    ) -> None:
        """
        把指定元件引脚连接到网络。
        """

        pin_id = f"{reference}:{pin_number}"

        if pin_id not in self.graph:
            raise ValueError(
                f"Pin does not exist: {pin_id}"
            )

        net_id = self.add_net(net_name)

        self.graph.add_edge(
            pin_id,
            net_id,
            relation="connected_to",
        )

    def get_components(self) -> list[tuple]:
        return [
            (node_id, data)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("node_type") == "Component"
        ]

    def get_pins(self) -> list[tuple]:
        return [
            (node_id, data)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("node_type") == "Pin"
        ]

    def get_nets(self) -> list[tuple]:
        return [
            (node_id, data)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("node_type") == "Net"
        ]

    def get_net_connections(
        self,
        net_name: str,
    ) -> list[dict[str, str]]:
        """
        查询某个网络包含的全部引脚。
        """

        net_id = f"net:{net_name}"

        if net_id not in self.graph:
            raise KeyError(
                f"Net does not exist: {net_name}"
            )

        connections = []

        for neighbor in self.graph.neighbors(net_id):
            data = self.graph.nodes[neighbor]

            if data.get("node_type") != "Pin":
                continue

            connections.append(
                {
                    "reference": data["reference"],
                    "pin_number": data["pin_number"],
                    "pin_name": data["pin_name"],
                }
            )

        return connections

    def show(self) -> None:
        print("=" * 60)
        print("SCHEMATIC CIRCUIT GRAPH")
        print("=" * 60)

        print("\nComponents:")
        for reference, data in self.get_components():
            print(
                f"- {reference}: "
                f"{data.get('component_type')} "
                f"{data.get('part_number') or data.get('value')}"
            )

        print("\nPins:")
        for pin_id, data in self.get_pins():
            print(
                f"- {pin_id}: {data.get('pin_name')}"
            )

        print("\nNets:")
        for _, net_data in self.get_nets():
            net_name = net_data["name"]
            connections = self.get_net_connections(net_name)

            formatted_connections = [
                (
                    f"{item['reference']}."
                    f"{item['pin_name']}"
                    f"({item['pin_number']})"
                )
                for item in connections
            ]

            print(
                f"- {net_name}: "
                + ", ".join(formatted_connections)
            )

        print("\nStatistics:")
        print(
            f"- Components: {len(self.get_components())}"
        )
        print(
            f"- Pins: {len(self.get_pins())}"
        )
        print(
            f"- Nets: {len(self.get_nets())}"
        )