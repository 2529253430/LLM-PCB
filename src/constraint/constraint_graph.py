from typing import Any

import networkx as nx


class ConstraintGraph:
    """
    PCB 设计约束图。

    节点用于表示需求、拓扑、器件和规则。
    边用于表示节点之间的关系。
    """

    def __init__(self) -> None:
        # DiGraph 表示有方向的图：
        # 例如 Design --selects_topology--> Buck
        self.graph = nx.DiGraph()

    def add_node(
        self,
        node_id: str,
        node_type: str,
        **attributes: Any,
    ) -> None:
        """
        添加一个节点。

        node_id:
            节点的唯一名称，例如 requirement_vin。

        node_type:
            节点类型，例如 Design、Requirement、Topology。
        """
        self.graph.add_node(
            node_id,
            node_type=node_type,
            **attributes,
        )

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        **attributes: Any,
    ) -> None:
        """
        添加一条有方向的关系。

        例如：
        design -> topology_buck
        relation = selects_topology
        """
        if source not in self.graph:
            raise ValueError(f"Source node does not exist: {source}")

        if target not in self.graph:
            raise ValueError(f"Target node does not exist: {target}")

        self.graph.add_edge(
            source,
            target,
            relation=relation,
            **attributes,
        )

    def get_nodes_by_type(self, node_type: str) -> list[tuple]:
        """
        按节点类型查找节点。
        """
        return [
            (node_id, data)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("node_type") == node_type
        ]

    def get_node(self, node_id: str) -> dict[str, Any]:
        """
        获取一个节点的属性。
        """
        if node_id not in self.graph:
            raise KeyError(f"Node does not exist: {node_id}")

        return dict(self.graph.nodes[node_id])

    def show(self) -> None:
        """
        在终端中显示所有节点和关系。
        """
        print("=" * 60)
        print("KNOWLEDGE-AWARE CONSTRAINT GRAPH")
        print("=" * 60)

        print("\nNodes:")
        for node_id, data in self.graph.nodes(data=True):
            print(f"- {node_id}")
            print(f"  {data}")

        print("\nEdges:")
        for source, target, data in self.graph.edges(data=True):
            relation = data.get("relation", "related_to")
            print(f"- {source} --[{relation}]--> {target}")

        print("\nGraph Statistics:")
        print(f"- Number of nodes: {self.graph.number_of_nodes()}")
        print(f"- Number of edges: {self.graph.number_of_edges()}")