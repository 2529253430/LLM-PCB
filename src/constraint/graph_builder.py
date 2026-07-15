from src.constraint.constraint_graph import ConstraintGraph
from src.selector.topology_selector import select_topology


class GraphBuilder:
    """
    根据用户的结构化需求建立约束图。
    """

    def build(
        self,
        vin: float,
        vout: float,
        current: float,
        priority: str = "Balanced",
    ) -> ConstraintGraph:
        """
        建立第一版设计约束图。
        """

        self._validate_inputs(vin, vout, current)

        graph = ConstraintGraph()

        # 1. 创建整个设计的根节点
        graph.add_node(
            node_id="design",
            node_type="Design",
            name="Power Converter Design",
        )

        # 2. 创建输入电压需求节点
        graph.add_node(
            node_id="requirement_vin",
            node_type="Requirement",
            name="Vin",
            value=vin,
            unit="V",
        )

        graph.add_edge(
            source="design",
            target="requirement_vin",
            relation="has_requirement",
        )

        # 3. 创建输出电压需求节点
        graph.add_node(
            node_id="requirement_vout",
            node_type="Requirement",
            name="Vout",
            value=vout,
            unit="V",
        )

        graph.add_edge(
            source="design",
            target="requirement_vout",
            relation="has_requirement",
        )

        # 4. 创建输出电流需求节点
        graph.add_node(
            node_id="requirement_current",
            node_type="Requirement",
            name="Output Current",
            value=current,
            unit="A",
        )

        graph.add_edge(
            source="design",
            target="requirement_current",
            relation="has_requirement",
        )

        # 5. 创建设计优先级节点
        graph.add_node(
            node_id="requirement_priority",
            node_type="Preference",
            name="Design Priority",
            value=priority,
        )

        graph.add_edge(
            source="design",
            target="requirement_priority",
            relation="has_preference",
        )

        # 6. 调用已经完成的拓扑选择器
        topology = select_topology(vin, vout)

        topology_node_id = f"topology_{topology.lower()}"

        graph.add_node(
            node_id=topology_node_id,
            node_type="Topology",
            name=topology,
        )

        graph.add_edge(
            source="design",
            target=topology_node_id,
            relation="selects_topology",
            reason=self._topology_reason(vin, vout),
        )

        # 7. 把功率作为推导出来的约束加入图中
        output_power = vout * current

        graph.add_node(
            node_id="derived_output_power",
            node_type="DerivedConstraint",
            name="Output Power",
            value=output_power,
            unit="W",
        )

        graph.add_edge(
            source="requirement_vout",
            target="derived_output_power",
            relation="contributes_to",
        )

        graph.add_edge(
            source="requirement_current",
            target="derived_output_power",
            relation="contributes_to",
        )

        return graph

    @staticmethod
    def _validate_inputs(
        vin: float,
        vout: float,
        current: float,
    ) -> None:
        """
        检查输入参数是否合法。
        """

        if vin <= 0:
            raise ValueError("Input voltage must be greater than 0.")

        if vout <= 0:
            raise ValueError("Output voltage must be greater than 0.")

        if current <= 0:
            raise ValueError("Output current must be greater than 0.")

    @staticmethod
    def _topology_reason(vin: float, vout: float) -> str:
        """
        给出拓扑判断原因，增强系统可解释性。
        """

        if vin > vout:
            return "Vin is greater than Vout, so a step-down topology is required."

        if vin < vout:
            return "Vin is lower than Vout, so a step-up topology is required."

        return "Vin equals Vout; no voltage conversion direction is determined."


if __name__ == "__main__":
    builder = GraphBuilder()

    constraint_graph = builder.build(
    vin=24
    vout=5
    current=3
    priority="Efficiency",)

    constraint_graph.show()