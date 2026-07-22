from src.constraint.constraint_graph import ConstraintGraph
from src.schematic.circuit_graph import CircuitGraph


class SchematicGenerator:
    """
    根据 Constraint Graph 生成 Buck 原理图 Circuit Graph。

    当前版本使用 TPS5430 的真实物理引脚编号：

    VIN  -> Pin 6
    SW   -> Pin 7
    FB   -> Pin 3
    GND  -> Pin 5

    说明：
    TPS5430 的 SW 实际对应 Pin 7 和 Pin 8，
    GND 实际对应 Pin 5 和 PowerPAD Pin 9。

    当前第一版原理图使用主引脚：
    SW 使用 Pin 7；
    GND 使用 Pin 5。

    后续导出 KiCad 和 PCB 时，再补充并联的
    Pin 8 和 PowerPAD Pin 9。
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

        self._add_passive_components(
            graph=graph
        )

        self._connect_buck_nets(
            graph=graph
        )

        return graph

    @staticmethod
    def _select_best_controller(
        constraint_graph: ConstraintGraph,
    ) -> dict:
        """
        从 Constraint Graph 中选择 rank 最小的控制器。

        rank=1 表示当前推荐顺序中的第一名。
        """

        candidates = []

        for _, data in (
            constraint_graph.graph.nodes(
                data=True
            )
        ):
            if (
                data.get("node_type")
                != "ComponentCandidate"
            ):
                continue

            candidates.append(
                dict(data)
            )

        if not candidates:
            raise ValueError(
                "No controller candidates found "
                "in the constraint graph."
            )

        candidates.sort(
            key=lambda item: item.get(
                "rank",
                999,
            )
        )

        return candidates[0]

    @staticmethod
    def _add_controller(
        graph: CircuitGraph,
        controller: dict,
    ) -> None:
        """
        添加 Buck 控制器和真实物理引脚。

        当前控制器统一按 TPS5430DDA 建模。
        """

        selected_name = str(
            controller.get(
                "name",
                "TPS5430DDA",
            )
        )

        # 为了保证当前真实器件库和封装库能够匹配，
        # 第一版固定使用 TPS5430DDA。
        #
        # 后续如果器件数据库中加入其他真实器件库，
        # 可以改为直接使用 selected_name。
        part_number = "TPS5430DDA"

        graph.add_component(
            reference="U1",
            component_type="Controller",
            part_number=part_number,
            manufacturer=controller.get(
                "manufacturer",
                "Texas Instruments",
            ),
            package=controller.get(
                "package",
                "SOIC-8 PowerPAD",
            ),
            footprint_name=(
                "SOIC-8-PowerPAD-DDA"
            ),
            selected_candidate=selected_name,
            efficiency=controller.get(
                "efficiency",
                0,
            ),
        )

        # TPS5430 真实物理引脚编号
        graph.add_pin(
            reference="U1",
            pin_number="6",
            pin_name="VIN",
        )

        graph.add_pin(
            reference="U1",
            pin_number="7",
            pin_name="SW",
        )

        graph.add_pin(
            reference="U1",
            pin_number="3",
            pin_name="FB",
        )

        graph.add_pin(
            reference="U1",
            pin_number="5",
            pin_name="GND",
        )

    @staticmethod
    def _add_passive_components(
        graph: CircuitGraph,
    ) -> None:
        """
        添加 Buck 外围无源元件。

        当前无源器件仍使用简化的两引脚模型。
        """

        graph.add_component(
            reference="CIN",
            component_type="Input Capacitor",
            value="22uF",
        )

        graph.add_pin(
            reference="CIN",
            pin_number="1",
            pin_name="POS",
        )

        graph.add_pin(
            reference="CIN",
            pin_number="2",
            pin_name="NEG",
        )

        graph.add_component(
            reference="L1",
            component_type="Inductor",
            value="10uH",
        )

        graph.add_pin(
            reference="L1",
            pin_number="1",
            pin_name="IN",
        )

        graph.add_pin(
            reference="L1",
            pin_number="2",
            pin_name="OUT",
        )

        graph.add_component(
            reference="COUT",
            component_type="Output Capacitor",
            value="100uF",
        )

        graph.add_pin(
            reference="COUT",
            pin_number="1",
            pin_name="POS",
        )

        graph.add_pin(
            reference="COUT",
            pin_number="2",
            pin_name="NEG",
        )

        graph.add_component(
            reference="R1",
            component_type="Feedback Resistor",
            value="100k",
        )

        graph.add_pin(
            reference="R1",
            pin_number="1",
            pin_name="HIGH",
        )

        graph.add_pin(
            reference="R1",
            pin_number="2",
            pin_name="LOW",
        )

        graph.add_component(
            reference="R2",
            component_type="Feedback Resistor",
            value="19.1k",
        )

        graph.add_pin(
            reference="R2",
            pin_number="1",
            pin_name="HIGH",
        )

        graph.add_pin(
            reference="R2",
            pin_number="2",
            pin_name="LOW",
        )

    @staticmethod
    def _connect_buck_nets(
        graph: CircuitGraph,
    ) -> None:
        """
        建立标准 Buck 电路网络。

        U1 使用 TPS5430 的真实物理引脚编号。
        """

        # VIN 输入网络
        graph.connect_pin(
            reference="U1",
            pin_number="6",
            net_name="VIN",
        )

        graph.connect_pin(
            reference="CIN",
            pin_number="1",
            net_name="VIN",
        )

        # SW 开关网络
        graph.connect_pin(
            reference="U1",
            pin_number="7",
            net_name="SW",
        )

        graph.connect_pin(
            reference="L1",
            pin_number="1",
            net_name="SW",
        )

        # VOUT 输出网络
        graph.connect_pin(
            reference="L1",
            pin_number="2",
            net_name="VOUT",
        )

        graph.connect_pin(
            reference="COUT",
            pin_number="1",
            net_name="VOUT",
        )

        graph.connect_pin(
            reference="R1",
            pin_number="1",
            net_name="VOUT",
        )

        # FB 反馈网络
        graph.connect_pin(
            reference="U1",
            pin_number="3",
            net_name="FB",
        )

        graph.connect_pin(
            reference="R1",
            pin_number="2",
            net_name="FB",
        )

        graph.connect_pin(
            reference="R2",
            pin_number="1",
            net_name="FB",
        )

        # GND 地网络
        graph.connect_pin(
            reference="U1",
            pin_number="5",
            net_name="GND",
        )

        graph.connect_pin(
            reference="CIN",
            pin_number="2",
            net_name="GND",
        )

        graph.connect_pin(
            reference="COUT",
            pin_number="2",
            net_name="GND",
        )

        graph.connect_pin(
            reference="R2",
            pin_number="2",
            net_name="GND",
        )


if __name__ == "__main__":
    print(
        "Run this module through "
        "test/test_schematic_pipeline.py"
    )