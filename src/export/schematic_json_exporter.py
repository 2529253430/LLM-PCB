import json
from pathlib import Path
from typing import Any

from src.schematic.circuit_graph import CircuitGraph


class SchematicJsonExporter:
    """
    将 CircuitGraph 导出为标准 JSON 中间表示。
    """

    FORMAT_NAME = "LLM-PCB-Schematic"
    FORMAT_VERSION = "1.0"

    def export(
        self,
        circuit_graph: CircuitGraph,
        output_path: Path,
        topology: str,
    ) -> Path:
        """
        将原理图导出到指定 JSON 文件。

        参数：
        circuit_graph:
            已经生成的 CircuitGraph。

        output_path:
            目标 JSON 文件路径。

        topology:
            电路拓扑，例如 Buck 或 Boost。
        """

        document = self.to_dict(
            circuit_graph=circuit_graph,
            topology=topology,
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                document,
                file,
                ensure_ascii=False,
                indent=2,
            )

        return output_path

    def to_dict(
        self,
        circuit_graph: CircuitGraph,
        topology: str,
    ) -> dict[str, Any]:
        """
        将 CircuitGraph 转换成 Python 字典。
        """

        return {
            "metadata": self._build_metadata(topology),
            "components": self._build_components(
                circuit_graph
            ),
            "nets": self._build_nets(
                circuit_graph
            ),
            "statistics": self._build_statistics(
                circuit_graph
            ),
        }

    def _build_metadata(
        self,
        topology: str,
    ) -> dict[str, str]:
        """
        生成文件基本信息。
        """

        return {
            "format": self.FORMAT_NAME,
            "version": self.FORMAT_VERSION,
            "topology": topology,
        }

    @staticmethod
    def _build_components(
        circuit_graph: CircuitGraph,
    ) -> list[dict[str, Any]]:
        """
        导出所有元件及其引脚。
        """

        components = []

        for reference, component_data in (
            circuit_graph.get_components()
        ):
            pins = []

            for neighbor in circuit_graph.graph.neighbors(
                reference
            ):
                pin_data = circuit_graph.graph.nodes[
                    neighbor
                ]

                if pin_data.get("node_type") != "Pin":
                    continue

                pins.append(
                    {
                        "pin_number": pin_data.get(
                            "pin_number",
                            "",
                        ),
                        "pin_name": pin_data.get(
                            "pin_name",
                            "",
                        ),
                    }
                )

            pins.sort(
                key=lambda item: str(
                    item["pin_number"]
                )
            )

            components.append(
                {
                    "reference": reference,
                    "component_type": component_data.get(
                        "component_type",
                        "",
                    ),
                    "part_number": component_data.get(
                        "part_number",
                        "",
                    ),
                    "value": component_data.get(
                        "value",
                        "",
                    ),
                    "manufacturer": component_data.get(
                        "manufacturer",
                        "",
                    ),
                    "package": component_data.get(
                        "package",
                        "",
                    ),
                    "pins": pins,
                }
            )

        components.sort(
            key=lambda item: item["reference"]
        )

        return components

    @staticmethod
    def _build_nets(
        circuit_graph: CircuitGraph,
    ) -> list[dict[str, Any]]:
        """
        导出所有网络及其连接引脚。
        """

        nets = []

        for _, net_data in circuit_graph.get_nets():
            net_name = net_data["name"]

            connections = (
                circuit_graph.get_net_connections(
                    net_name
                )
            )

            connections.sort(
                key=lambda item: (
                    item["reference"],
                    str(item["pin_number"]),
                )
            )

            nets.append(
                {
                    "name": net_name,
                    "connections": connections,
                }
            )

        nets.sort(
            key=lambda item: item["name"]
        )

        return nets

    @staticmethod
    def _build_statistics(
        circuit_graph: CircuitGraph,
    ) -> dict[str, int]:
        """
        导出原理图统计信息。
        """

        return {
            "component_count": len(
                circuit_graph.get_components()
            ),
            "pin_count": len(
                circuit_graph.get_pins()
            ),
            "net_count": len(
                circuit_graph.get_nets()
            ),
        }