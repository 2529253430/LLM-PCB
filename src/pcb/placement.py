from src.constraint.constraint_graph import (
    ConstraintGraph,
)
from src.pcb.board import PCBBoard
from src.schematic.circuit_graph import (
    CircuitGraph,
)


class TopologyAwarePlacementEngine:
    """
    基于拓扑和布局规则生成初始 PCB 坐标。
    """

    def place_buck(
        self,
        circuit_graph: CircuitGraph,
        constraint_graph: ConstraintGraph,
        board_width: float = 100.0,
        board_height: float = 80.0,
    ) -> PCBBoard:
        """
        为 Buck 电路生成第一版规则驱动布局。
        """

        self._validate_required_components(
            circuit_graph
        )

        placement_rules = (
            self._extract_placement_rules(
                constraint_graph
            )
        )

        board = PCBBoard(
            width=board_width,
            height=board_height,
            unit="mm",
        )

        center_y = board_height / 2

        # 主功率路径：
        # VIN → CIN → U1 → L1 → COUT → VOUT
        board.place_component(
            reference="CIN",
            component_type="Input Capacitor",
            x=15.0,
            y=center_y,
            width=8.0,
            height=8.0,
            applied_rule=self._find_rule(
                placement_rules,
                "Input Capacitor",
            ),
        )

        selected_part = self._get_part_number(
        circuit_graph,
         "U1",
       )

        board.place_component(
        reference="U1",
        component_type="Controller",
        x=32.0,
        y=center_y,
        rotation=0.0,
        width=12.0,
        height=10.0,
        part_number=selected_part,
        footprint_name="SOIC-8-PowerPAD-DDA",
     )

        board.place_component(
            reference="L1",
            component_type="Inductor",
            x=52.0,
            y=center_y,
            width=10.0,
            height=10.0,
            applied_rule=self._find_rule(
                placement_rules,
                "Inductor",
            ),
        )

        board.place_component(
            reference="COUT",
            component_type="Output Capacitor",
            x=72.0,
            y=center_y,
            width=10.0,
            height=10.0,
        )

        # 反馈网络放在控制器下方，
        # 与 SW 主功率路径保持距离。
        feedback_y = center_y + 22.0

        board.place_component(
            reference="R1",
            component_type="Feedback Resistor",
            x=36.0,
            y=feedback_y,
            width=6.0,
            height=3.0,
            applied_rule=self._find_rule(
                placement_rules,
                "Feedback Resistor",
            ),
        )

        board.place_component(
            reference="R2",
            component_type="Feedback Resistor",
            x=48.0,
            y=feedback_y,
            width=6.0,
            height=3.0,
            applied_rule=self._find_rule(
                placement_rules,
                "Feedback Resistor",
            ),
        )

        return board

    @staticmethod
    def _validate_required_components(
        circuit_graph: CircuitGraph,
    ) -> None:
        """
        检查 Buck 原理图是否包含全部必需元件。
        """

        existing_references = {
            reference
            for reference, _ in (
                circuit_graph.get_components()
            )
        }

        required_references = {
            "U1",
            "CIN",
            "L1",
            "COUT",
            "R1",
            "R2",
        }

        missing_references = (
            required_references
            - existing_references
        )

        if missing_references:
            raise ValueError(
                "Missing required schematic "
                f"components: {sorted(missing_references)}"
            )

    @staticmethod
    def _extract_placement_rules(
        constraint_graph: ConstraintGraph,
    ) -> list[dict]:
        """
        从 Constraint Graph 中读取布局规则。
        """

        rules = []

        for _, data in (
            constraint_graph.graph.nodes(
                data=True
            )
        ):
            if (
                data.get("node_type")
                != "PlacementRule"
            ):
                continue

            rules.append(dict(data))

        return rules

    @staticmethod
    def _find_rule(
        placement_rules: list[dict],
        component_name: str,
    ) -> str:
        """
        查找某种元件对应的布局规则。
        """

        normalized_name = (
            component_name.strip().lower()
        )

        for rule in placement_rules:
            existing_name = str(
                rule.get("component", "")
            ).strip().lower()

            if existing_name == normalized_name:
                return str(
                    rule.get("rule", "")
                )

        return ""

    @staticmethod
    def validate_buck_placement(
        board: PCBBoard,
    ) -> list[str]:
        """
        检查第一版 Buck 布局规则。

        返回违反规则的提示列表。
        空列表表示通过。
        """

        violations = []

        cin_u1_distance = board.get_distance(
            "CIN",
            "U1",
        )

        u1_l1_distance = board.get_distance(
            "U1",
            "L1",
        )

        r1_l1_distance = board.get_distance(
            "R1",
            "L1",
        )

        if cin_u1_distance > 20.0:
            violations.append(
                "CIN is too far from U1."
            )

        if u1_l1_distance > 25.0:
            violations.append(
                "L1 is too far from U1."
            )

        if r1_l1_distance < 18.0:
            violations.append(
                "Feedback network is too close "
                "to the switching inductor."
            )

        return violations

    @staticmethod
    def _get_part_number(
        circuit_graph: CircuitGraph,
        reference: str,
    ) -> str:
        """
        从 Circuit Graph 中读取器件型号。
        """

        if reference not in circuit_graph.graph:
            raise KeyError(
                f"Component does not exist: {reference}"
            )

        data = circuit_graph.graph.nodes[
            reference
        ]

        return str(
            data.get("part_number", "")
        )