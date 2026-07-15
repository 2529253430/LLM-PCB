from src.constraint.constraint_graph import ConstraintGraph
from src.schematic.circuit_graph import CircuitGraph


class SchematicGenerator:
    """
    根据 Constraint Graph 生成原理图 Circuit Graph。
    """

    def generate_buck(
        self,
        constraint_graph: ConstraintGraph,
    ) -> CircuitGraph:
        """
        生成 Buck 电路的元件、引脚和网络。
        """

        controller = self._select_best_controller(
            constraint_graph
        )

        graph = CircuitGraph()

        self._add_controller(
            graph=graph,
            controller=controller,
        )

        self._add_passive_components(graph)
        self._connect_buck_nets(graph)

        return graph

    @staticmethod
    def _select_best_controller(
        constraint_graph: ConstraintGraph,
    ) -> dict:
        """
        从约束图中选择 rank=1 的控制器。
        """

        candidates = []

        for _, data in constraint_graph.graph.nodes(
            data=True
        ):
            if data.get("node_type") != "ComponentCandidate":
                continue

            candidates.append(dict(data))

        if not candidates:
            raise ValueError(
                "No controller candidates found "
                "in the constraint graph."
            )

        candidates.sort(
            key=lambda item: item.get("rank", 999)
        )

        return candidates[0]

    @staticmethod
    def _add_controller(
        graph: CircuitGraph,
        controller: dict,
    ) -> None:
        """
        添加控制器及其逻辑引脚。

        当前先使用通用 Buck 引脚名称。
        后续会由器件引脚数据库替代。
        """

        graph.add_component(
            reference="U1",
            component_type="Controller",
            part_number=controller["name"],
            manufacturer=controller.get(
                "manufacturer",
                "",
            ),
            package=controller.get(
                "package",
                "",
            ),
            efficiency=controller.get(
                "efficiency",
                0,
            ),
        )

        graph.add_pin("U1", "VIN", "VIN")
        graph.add_pin("U1", "SW", "SW")
        graph.add_pin("U1", "FB", "FB")
        graph.add_pin("U1", "GND", "GND")

    @staticmethod
    def _add_passive_components(
        graph: CircuitGraph,
    ) -> None:
        """
        添加 Buck 外围元件。
        """

        graph.add_component(
            reference="CIN",
            component_type="Input Capacitor",
            value="22uF",
        )
        graph.add_pin("CIN", "1", "POS")
        graph.add_pin("CIN", "2", "NEG")

        graph.add_component(
            reference="L1",
            component_type="Inductor",
            value="10uH",
        )
        graph.add_pin("L1", "1", "IN")
        graph.add_pin("L1", "2", "OUT")

        graph.add_component(
            reference="COUT",
            component_type="Output Capacitor",
            value="100uF",
        )
        graph.add_pin("COUT", "1", "POS")
        graph.add_pin("COUT", "2", "NEG")

        graph.add_component(
            reference="R1",
            component_type="Feedback Resistor",
            value="100k",
        )
        graph.add_pin("R1", "1", "HIGH")
        graph.add_pin("R1", "2", "LOW")

        graph.add_component(
            reference="R2",
            component_type="Feedback Resistor",
            value="19.1k",
        )
        graph.add_pin("R2", "1", "HIGH")
        graph.add_pin("R2", "2", "LOW")

    @staticmethod
    def _connect_buck_nets(
        graph: CircuitGraph,
    ) -> None:
        """
        建立标准 Buck 电路网络。
        """

        # 输入网络
        graph.connect_pin("U1", "VIN", "VIN")
        graph.connect_pin("CIN", "1", "VIN")

        # 开关网络
        graph.connect_pin("U1", "SW", "SW")
        graph.connect_pin("L1", "1", "SW")

        # 输出网络
        graph.connect_pin("L1", "2", "VOUT")
        graph.connect_pin("COUT", "1", "VOUT")
        graph.connect_pin("R1", "1", "VOUT")

        # 反馈网络
        graph.connect_pin("U1", "FB", "FB")
        graph.connect_pin("R1", "2", "FB")
        graph.connect_pin("R2", "1", "FB")

        # 地网络
        graph.connect_pin("U1", "GND", "GND")
        graph.connect_pin("CIN", "2", "GND")
        graph.connect_pin("COUT", "2", "GND")
        graph.connect_pin("R2", "2", "GND")