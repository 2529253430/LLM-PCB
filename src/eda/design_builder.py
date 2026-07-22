from __future__ import annotations

from typing import Any

from src.database.component_instance import (
    ComponentInstance,
)
from src.eda.design import (
    EDAComponent,
    EDADesign,
    EDAPad,
    EDAPoint,
    EDARoutedNet,
    EDARouteSegment,
)
from src.pcb.board import (
    PCBBoard,
    PlacedComponent,
)
from src.pcb.route import RoutingResult
from src.schematic.circuit_graph import CircuitGraph


class EDADesignBuilder:
    """
    将现有的原理图、布局和布线结果
    转换为统一的 EDADesign 模型。

    输入：
    - CircuitGraph
    - PCBBoard
    - RoutingResult

    输出：
    - EDADesign
    """

    def build(
        self,
        name: str,
        topology: str,
        circuit_graph: CircuitGraph,
        board: PCBBoard,
        routing_result: RoutingResult,
    ) -> EDADesign:
        """
        建立完整 EDA Design Model。
        """

        design = EDADesign(
            name=name,
            topology=topology,
            board_width=board.width,
            board_height=board.height,
            unit=board.unit,
        )

        self._add_components(
            design=design,
            circuit_graph=circuit_graph,
            board=board,
        )

        self._add_nets(
            design=design,
            circuit_graph=circuit_graph,
        )

        self._add_routes(
            design=design,
            routing_result=routing_result,
        )

        self._add_metadata(
            design=design,
        )

        errors = design.validate()

        if errors:
            raise ValueError(
                "EDA design validation failed: "
                + "; ".join(errors)
            )

        return design

    def _add_components(
        self,
        design: EDADesign,
        circuit_graph: CircuitGraph,
        board: PCBBoard,
    ) -> None:
        """
        将 CircuitGraph 和 PCBBoard 中的器件
        转换为 EDAComponent。
        """

        for reference, component_data in (
            circuit_graph.get_components()
        ):
            placed_component = (
                board.get_component(reference)
            )

            eda_component = (
                self._build_component(
                    reference=reference,
                    component_data=component_data,
                    placed_component=(
                        placed_component
                    ),
                    circuit_graph=circuit_graph,
                )
            )

            design.add_component(
                eda_component
            )

    def _build_component(
        self,
        reference: str,
        component_data: dict[str, Any],
        placed_component: PlacedComponent,
        circuit_graph: CircuitGraph,
    ) -> EDAComponent:
        """
        建立一个具体的 EDAComponent。
        """

        part_number = str(
            component_data.get(
                "part_number",
                "",
            )
        )

        component_type = str(
            component_data.get(
                "component_type",
                "",
            )
        )

        value = str(
            component_data.get(
                "value",
                "",
            )
        )

        manufacturer = str(
            component_data.get(
                "manufacturer",
                "",
            )
        )

        symbol_name = self._get_symbol_name(
            component_data=component_data,
            component_type=component_type,
        )

        footprint_name = self._get_footprint_name(
            component_data=component_data,
            placed_component=placed_component,
            component_type=component_type,
        )

        eda_component = EDAComponent(
            reference=reference,
            part_number=part_number,
            component_type=component_type,
            symbol_name=symbol_name,
            footprint_name=footprint_name,
            position=EDAPoint(
                x=placed_component.x,
                y=placed_component.y,
            ),
            rotation=placed_component.rotation,
            value=value,
            manufacturer=manufacturer,
            attributes={
                **component_data,
                **placed_component.attributes,
            },
        )

        if part_number:
            self._add_real_component_pads(
                eda_component=eda_component,
                part_number=part_number,
                placed_component=placed_component,
            )
        else:
            self._add_simplified_passive_pads(
                eda_component=eda_component,
                reference=reference,
                placed_component=placed_component,
                circuit_graph=circuit_graph,
            )

        return eda_component

    @staticmethod
    def _get_symbol_name(
        component_data: dict[str, Any],
        component_type: str,
    ) -> str:
        """
        获取原理图符号名称。
        """

        explicit_symbol = str(
            component_data.get(
                "symbol_name",
                "",
            )
        ).strip()

        if explicit_symbol:
            return explicit_symbol

        symbol_mapping = {
            "Controller": "TPS5430",
            "Input Capacitor": "C",
            "Output Capacitor": "C",
            "Inductor": "L",
            "Feedback Resistor": "R",
        }

        return symbol_mapping.get(
            component_type,
            component_type.replace(" ", "_"),
        )

    @staticmethod
    def _get_footprint_name(
        component_data: dict[str, Any],
        placed_component: PlacedComponent,
        component_type: str,
    ) -> str:
        """
        获取 PCB 封装名称。

        U1 使用真实封装；
        无源器件暂时使用简化封装名称。
        """

        explicit_footprint = str(
            component_data.get(
                "footprint_name",
                "",
            )
        ).strip()

        if explicit_footprint:
            return explicit_footprint

        placed_footprint = str(
            placed_component.footprint_name
        ).strip()

        if placed_footprint:
            return placed_footprint

        footprint_mapping = {
            "Input Capacitor": "C_1210",
            "Output Capacitor": "C_1210",
            "Inductor": "L_Power_10mm",
            "Feedback Resistor": "R_0603",
        }

        return footprint_mapping.get(
            component_type,
            "Generic_Footprint",
        )

    @staticmethod
    def _add_real_component_pads(
        eda_component: EDAComponent,
        part_number: str,
        placed_component: PlacedComponent,
    ) -> None:
        """
        使用 ComponentInstance 建立真实焊盘。
        """

        instance = ComponentInstance(
            reference=eda_component.reference,
            part_number=part_number,
            x=placed_component.x,
            y=placed_component.y,
            rotation=placed_component.rotation,
        )

        pin_name_map = {
            str(pin.get("number", "")): str(
                pin.get("name", "")
            )
            for pin in instance.part_data.get(
                "pins",
                [],
            )
        }

        for pad_position in (
            instance.get_all_pad_positions()
        ):
            pad_number = (
                pad_position.pad_number
            )

            eda_component.add_pad(
                EDAPad(
                    number=pad_number,
                    name=pin_name_map.get(
                        pad_number,
                        f"PAD_{pad_number}",
                    ),
                    position=EDAPoint(
                        x=pad_position.x,
                        y=pad_position.y,
                    ),
                    width=pad_position.width,
                    height=pad_position.height,
                    shape="rect",
                    layer="F.Cu",
                )
            )

    @staticmethod
    def _add_simplified_passive_pads(
        eda_component: EDAComponent,
        reference: str,
        placed_component: PlacedComponent,
        circuit_graph: CircuitGraph,
    ) -> None:
        """
        为无源器件建立简化双焊盘模型。

        Pin 1 位于元件左侧；
        Pin 2 位于元件右侧。
        """

        pin_nodes = []

        for neighbor in (
            circuit_graph.graph.neighbors(
                reference
            )
        ):
            node_data = (
                circuit_graph.graph.nodes[
                    neighbor
                ]
            )

            if (
                node_data.get("node_type")
                != "Pin"
            ):
                continue

            pin_nodes.append(
                dict(node_data)
            )

        pin_nodes.sort(
            key=lambda item: str(
                item.get(
                    "pin_number",
                    "",
                )
            )
        )

        for pin_data in pin_nodes:
            pin_number = str(
                pin_data.get(
                    "pin_number",
                    "",
                )
            )

            pin_name = str(
                pin_data.get(
                    "pin_name",
                    "",
                )
            )

            pad_x, pad_y = (
                EDADesignBuilder
                ._get_passive_pad_position(
                    placed_component=(
                        placed_component
                    ),
                    pin_number=pin_number,
                )
            )

            pad_width, pad_height = (
                EDADesignBuilder
                ._get_passive_pad_size(
                    component_type=(
                        eda_component
                        .component_type
                    )
                )
            )

            eda_component.add_pad(
                EDAPad(
                    number=pin_number,
                    name=pin_name,
                    position=EDAPoint(
                        x=pad_x,
                        y=pad_y,
                    ),
                    width=pad_width,
                    height=pad_height,
                    shape="rect",
                    layer="F.Cu",
                )
            )

    @staticmethod
    def _get_passive_pad_position(
        placed_component: PlacedComponent,
        pin_number: str,
    ) -> tuple[float, float]:
        """
        计算简化无源焊盘坐标。

        当前假设无源器件旋转角度为 0°。
        """

        normalized_pin = str(
            pin_number
        ).strip()

        if normalized_pin == "1":
            return (
                placed_component.x
                - placed_component.width / 2,
                placed_component.y,
            )

        if normalized_pin == "2":
            return (
                placed_component.x
                + placed_component.width / 2,
                placed_component.y,
            )

        return (
            placed_component.x,
            placed_component.y,
        )

    @staticmethod
    def _get_passive_pad_size(
        component_type: str,
    ) -> tuple[float, float]:
        """
        返回无源器件的简化焊盘尺寸。
        """

        size_mapping = {
            "Input Capacitor": (
                2.0,
                2.0,
            ),
            "Output Capacitor": (
                2.0,
                2.0,
            ),
            "Inductor": (
                2.5,
                3.0,
            ),
            "Feedback Resistor": (
                1.0,
                1.2,
            ),
        }

        return size_mapping.get(
            component_type,
            (
                1.0,
                1.0,
            ),
        )

    @staticmethod
    def _add_nets(
        design: EDADesign,
        circuit_graph: CircuitGraph,
    ) -> None:
        """
        将 CircuitGraph 中的网络连接
        转换为 EDANet。
        """

        for _, net_data in (
            circuit_graph.get_nets()
        ):
            net_name = str(
                net_data["name"]
            )

            connections = (
                circuit_graph
                .get_net_connections(
                    net_name
                )
            )

            for connection in connections:
                design.connect(
                    net_name=net_name,
                    reference=str(
                        connection[
                            "reference"
                        ]
                    ),
                    pad_number=str(
                        connection[
                            "pin_number"
                        ]
                    ),
                )

    @staticmethod
    def _add_routes(
        design: EDADesign,
        routing_result: RoutingResult,
    ) -> None:
        """
        将 RoutingResult 转换为
        EDARoutedNet 和 EDARouteSegment。
        """

        for routed_net in (
            routing_result.routed_nets.values()
        ):
            eda_routed_net = EDARoutedNet(
                net_name=routed_net.net_name
            )

            for connection in (
                routed_net.connections
            ):
                for segment in (
                    connection.segments
                ):
                    eda_routed_net.add_segment(
                        EDARouteSegment(
                            start=EDAPoint(
                                x=segment.start.x,
                                y=segment.start.y,
                            ),
                            end=EDAPoint(
                                x=segment.end.x,
                                y=segment.end.y,
                            ),
                            width=segment.width,
                            layer=(
                                EDADesignBuilder
                                ._convert_layer_name(
                                    segment.layer
                                )
                            ),
                        )
                    )

            design.add_routed_net(
                eda_routed_net
            )

    @staticmethod
    def _convert_layer_name(
        layer_name: str,
    ) -> str:
        """
        将项目内部层名称转换为
        KiCad 风格层名称。
        """

        layer_mapping = {
            "Top": "F.Cu",
            "Bottom": "B.Cu",
            "F.Cu": "F.Cu",
            "B.Cu": "B.Cu",
        }

        return layer_mapping.get(
            layer_name,
            layer_name,
        )

    @staticmethod
    def _add_metadata(
        design: EDADesign,
    ) -> None:
        """
        增加导出和追踪所需元数据。
        """

        design.metadata.update(
            {
                "generator": "LLM-PCB",
                "eda_model_version": "1.0",
                "target_export": (
                    "KiCad-compatible"
                ),
                "target_import": (
                    "Altium Designer"
                ),
            }
        )