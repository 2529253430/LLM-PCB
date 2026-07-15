from typing import Any
from src.selector.component_selector import select_component_records
from src.constraint.constraint_graph import ConstraintGraph
from src.knowledge.knowledge_loader import load_topology_knowledge


class KnowledgeEnricher:
    """
    将 PCB 拓扑知识加入 Constraint Graph。
    """

    def __init__(self) -> None:
        self.topology_knowledge = load_topology_knowledge()

    def enrich_topology(
        self,
        graph: ConstraintGraph,
        topology_name: str,
    ) -> ConstraintGraph:
        """
        根据拓扑名称，把描述、应用场景和必需器件加入图中。
        """

        if topology_name not in self.topology_knowledge:
            raise ValueError(
                f"Unsupported topology: {topology_name}"
            )

        topology_data = self.topology_knowledge[topology_name]
        topology_node_id = f"topology_{topology_name.lower()}"

        self._check_topology_node(graph, topology_node_id)

        self._add_topology_attributes(
            graph=graph,
            topology_node_id=topology_node_id,
            topology_data=topology_data,
        )

        self._add_required_components(
            graph=graph,
            topology_node_id=topology_node_id,
            topology_data=topology_data,
        )

        return graph

    def enrich_controller_candidates(
        self,
        graph: ConstraintGraph,
        topology_name: str,
        vin: float,
        vout: float,
        current: float,
        limit: int = 3,
    ) -> ConstraintGraph:
        """
        查询候选控制器，并加入约束图。
        """

        candidates = select_component_records(
            topology=topology_name,
            vin=vin,
            vout=vout,
            current=current,
            limit=limit,
        )

        controller_node_id = (
            "required_component_1_controller"
        )

        if controller_node_id not in graph.graph:
            raise ValueError(
                "Controller requirement node does not exist."
            )

        for rank, candidate in enumerate(
            candidates,
            start=1,
        ):
            part_number = candidate["PartNumber"]
            candidate_node_id = (
                f"candidate_controller_"
                f"{part_number.lower()}"
            )

            graph.add_node(
                node_id=candidate_node_id,
                node_type="ComponentCandidate",
                name=part_number,
                manufacturer=candidate.get(
                    "Manufacturer",
                    "",
                ),
                package=candidate.get(
                    "Package",
                    "",
                ),
                efficiency=float(
                    candidate.get("Efficiency", 0)
                ),
                current_rating=float(
                    candidate.get("Current", 0)
                ),
                rank=rank,
            )

            graph.add_edge(
                source=controller_node_id,
                target=candidate_node_id,
                relation="has_candidate",
                rank=rank,
            )

        return graph

    @staticmethod
    def _check_topology_node(
        graph: ConstraintGraph,
        topology_node_id: str,
    ) -> None:
        """
        检查拓扑节点是否已经存在。
        """

        if topology_node_id not in graph.graph:
            raise ValueError(
                f"Topology node does not exist: {topology_node_id}"
            )

    @staticmethod
    def _add_topology_attributes(
        graph: ConstraintGraph,
        topology_node_id: str,
        topology_data: dict[str, Any],
    ) -> None:
        """
        把拓扑描述和优缺点写入已有拓扑节点。
        """

        graph.graph.nodes[topology_node_id].update(
            {
                "description": topology_data.get(
                    "description",
                    "",
                ),
                "applications": topology_data.get(
                    "application",
                    [],
                ),
                "advantages": topology_data.get(
                    "advantages",
                    [],
                ),
                "disadvantages": topology_data.get(
                    "disadvantages",
                    [],
                ),
            }
        )

    @staticmethod
    def _add_required_components(
        graph: ConstraintGraph,
        topology_node_id: str,
        topology_data: dict[str, Any],
    ) -> None:
        """
        为拓扑建立必需器件类型节点。
        """

        required_components = topology_data.get(
            "required_components",
            [],
        )

        for index, component_type in enumerate(
            required_components,
            start=1,
        ):
            component_node_id = (
                f"required_component_{index}_"
                f"{component_type.lower().replace(' ', '_')}"
            )

            graph.add_node(
                node_id=component_node_id,
                node_type="RequiredComponentType",
                name=component_type,
            )

            graph.add_edge(
                source=topology_node_id,
                target=component_node_id,
                relation="requires",
            )



if __name__ == "__main__":
    from src.constraint.graph_builder import GraphBuilder

    builder = GraphBuilder()

    test_graph = builder.build(
        vin=24,
        vout=5,
        current=3,
        priority="Efficiency",
    )

    enricher = KnowledgeEnricher()

    enriched_graph = enricher.enrich_topology(
        graph=test_graph,
        topology_name="Buck",
    )

    enriched_graph = (
        enricher.enrich_controller_candidates(
            graph=enriched_graph,
            topology_name="Buck",
            vin=24,
            vout=5,
            current=3,
            limit=3,
        )
    )

    enriched_graph.show()