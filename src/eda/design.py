from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EDAPoint:
    """
    EDA 设计中的二维坐标点。

    默认单位由 EDADesign.unit 决定，
    当前项目统一使用 mm。
    """

    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
        }


@dataclass(frozen=True)
class EDAPad:
    """
    PCB 封装中的一个真实焊盘。
    """

    number: str
    name: str
    position: EDAPoint
    width: float
    height: float
    shape: str = "rect"
    layer: str = "F.Cu"
    net_name: str = ""

    def __post_init__(self) -> None:
        if not self.number.strip():
            raise ValueError(
                "Pad number cannot be empty."
            )

        if self.width <= 0:
            raise ValueError(
                "Pad width must be greater than 0."
            )

        if self.height <= 0:
            raise ValueError(
                "Pad height must be greater than 0."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "name": self.name,
            "position": self.position.to_dict(),
            "width": self.width,
            "height": self.height,
            "shape": self.shape,
            "layer": self.layer,
            "net_name": self.net_name,
        }


@dataclass
class EDAComponent:
    """
    EDA 工程中的一个具体器件实例。

    例如：
    U1 是 TPS5430DDA 在当前设计中的实例。
    """

    reference: str
    part_number: str
    component_type: str
    symbol_name: str
    footprint_name: str
    position: EDAPoint
    rotation: float = 0.0
    value: str = ""
    manufacturer: str = ""
    pads: dict[str, EDAPad] = field(
        default_factory=dict
    )
    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError(
                "Component reference cannot be empty."
            )

        if not self.component_type.strip():
            raise ValueError(
                "Component type cannot be empty."
            )

        self.rotation = self.rotation % 360.0

    def add_pad(
        self,
        pad: EDAPad,
    ) -> None:
        """
        给器件添加真实焊盘。
        """

        if pad.number in self.pads:
            raise ValueError(
                f"Pad already exists on "
                f"{self.reference}: {pad.number}"
            )

        self.pads[pad.number] = pad

    def get_pad(
        self,
        pad_number: str,
    ) -> EDAPad:
        """
        根据编号获取焊盘。
        """

        normalized_number = str(
            pad_number
        ).strip()

        if normalized_number not in self.pads:
            raise KeyError(
                f"Pad not found on "
                f"{self.reference}: "
                f"{normalized_number}"
            )

        return self.pads[normalized_number]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "part_number": self.part_number,
            "component_type": self.component_type,
            "symbol_name": self.symbol_name,
            "footprint_name": self.footprint_name,
            "position": self.position.to_dict(),
            "rotation": self.rotation,
            "value": self.value,
            "manufacturer": self.manufacturer,
            "pads": [
                pad.to_dict()
                for pad in self.pads.values()
            ],
            "attributes": self.attributes,
        }


@dataclass(frozen=True)
class EDANetConnection:
    """
    一个网络与某个器件焊盘的连接关系。
    """

    reference: str
    pad_number: str

    def to_dict(self) -> dict[str, str]:
        return {
            "reference": self.reference,
            "pad_number": self.pad_number,
        }


@dataclass
class EDANet:
    """
    一条电气网络。

    例如：
    VIN、SW、VOUT、FB、GND。
    """

    name: str
    connections: list[
        EDANetConnection
    ] = field(default_factory=list)
    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "Net name cannot be empty."
            )

    def add_connection(
        self,
        connection: EDANetConnection,
    ) -> None:
        """
        给网络增加一个焊盘连接。
        """

        if connection in self.connections:
            raise ValueError(
                "Duplicate net connection: "
                f"{connection.reference}."
                f"{connection.pad_number}"
            )

        self.connections.append(connection)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connections": [
                connection.to_dict()
                for connection in self.connections
            ],
            "attributes": self.attributes,
        }


@dataclass(frozen=True)
class EDARouteSegment:
    """
    PCB 上的一段已布线铜线。
    """

    start: EDAPoint
    end: EDAPoint
    width: float
    layer: str = "F.Cu"

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError(
                "Route width must be greater than 0."
            )

        is_horizontal = (
            self.start.y == self.end.y
        )

        is_vertical = (
            self.start.x == self.end.x
        )

        if not (
            is_horizontal or is_vertical
        ):
            raise ValueError(
                "Current EDA route segment must "
                "be horizontal or vertical."
            )

    def length(self) -> float:
        return (
            abs(self.end.x - self.start.x)
            + abs(self.end.y - self.start.y)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "width": self.width,
            "layer": self.layer,
            "length": self.length(),
        }


@dataclass
class EDARoutedNet:
    """
    一条网络的全部走线段。
    """

    net_name: str
    segments: list[
        EDARouteSegment
    ] = field(default_factory=list)

    def add_segment(
        self,
        segment: EDARouteSegment,
    ) -> None:
        self.segments.append(segment)

    def total_length(self) -> float:
        return sum(
            segment.length()
            for segment in self.segments
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "net_name": self.net_name,
            "segments": [
                segment.to_dict()
                for segment in self.segments
            ],
            "total_length": self.total_length(),
        }


class EDADesign:
    """
    EDA 中间设计模型。

    后续 KiCad、Altium 等导出器只读取该模型，
    不直接依赖 CircuitGraph、PCBBoard 或
    RoutingResult。
    """

    def __init__(
        self,
        name: str,
        topology: str,
        board_width: float,
        board_height: float,
        unit: str = "mm",
    ) -> None:
        if not name.strip():
            raise ValueError(
                "Design name cannot be empty."
            )

        if not topology.strip():
            raise ValueError(
                "Topology cannot be empty."
            )

        if board_width <= 0:
            raise ValueError(
                "Board width must be greater than 0."
            )

        if board_height <= 0:
            raise ValueError(
                "Board height must be greater than 0."
            )

        self.name = name.strip()
        self.topology = topology.strip()
        self.board_width = float(
            board_width
        )
        self.board_height = float(
            board_height
        )
        self.unit = unit

        self.components: dict[
            str,
            EDAComponent,
        ] = {}

        self.nets: dict[
            str,
            EDANet,
        ] = {}

        self.routed_nets: dict[
            str,
            EDARoutedNet,
        ] = {}

        self.metadata: dict[
            str,
            Any,
        ] = {}

    def add_component(
        self,
        component: EDAComponent,
    ) -> None:
        """
        添加器件实例。
        """

        if (
            component.reference
            in self.components
        ):
            raise ValueError(
                "Component already exists: "
                f"{component.reference}"
            )

        self.components[
            component.reference
        ] = component

    def get_component(
        self,
        reference: str,
    ) -> EDAComponent:
        if reference not in self.components:
            raise KeyError(
                f"Component not found: {reference}"
            )

        return self.components[reference]

    def add_net(
        self,
        net: EDANet,
    ) -> None:
        """
        添加电气网络。
        """

        if net.name in self.nets:
            raise ValueError(
                f"Net already exists: {net.name}"
            )

        self.nets[net.name] = net

    def get_net(
        self,
        net_name: str,
    ) -> EDANet:
        if net_name not in self.nets:
            raise KeyError(
                f"Net not found: {net_name}"
            )

        return self.nets[net_name]

    def connect(
        self,
        net_name: str,
        reference: str,
        pad_number: str,
    ) -> None:
        """
        将器件焊盘连接到网络。

        同时检查器件和焊盘是否真实存在。
        """

        component = self.get_component(
            reference
        )

        component.get_pad(
            pad_number
        )

        if net_name not in self.nets:
            self.add_net(
                EDANet(name=net_name)
            )

        connection = EDANetConnection(
            reference=reference,
            pad_number=str(pad_number),
        )

        self.nets[
            net_name
        ].add_connection(connection)

    def add_routed_net(
        self,
        routed_net: EDARoutedNet,
    ) -> None:
        """
        添加一条已完成几何布线的网络。
        """

        if (
            routed_net.net_name
            not in self.nets
        ):
            raise KeyError(
                "Cannot add routing for "
                "undefined net: "
                f"{routed_net.net_name}"
            )

        if (
            routed_net.net_name
            in self.routed_nets
        ):
            raise ValueError(
                "Routing already exists for net: "
                f"{routed_net.net_name}"
            )

        self.routed_nets[
            routed_net.net_name
        ] = routed_net

    def validate(self) -> list[str]:
        """
        检查设计模型的基本一致性。

        返回空列表表示验证通过。
        """

        errors: list[str] = []

        for net in self.nets.values():
            if len(net.connections) < 2:
                errors.append(
                    f"Net {net.name} has fewer "
                    "than two connections."
                )

            for connection in net.connections:
                if (
                    connection.reference
                    not in self.components
                ):
                    errors.append(
                        f"Net {net.name} references "
                        "missing component "
                        f"{connection.reference}."
                    )
                    continue

                component = self.components[
                    connection.reference
                ]

                if (
                    connection.pad_number
                    not in component.pads
                ):
                    errors.append(
                        f"Net {net.name} references "
                        f"missing pad "
                        f"{connection.reference}."
                        f"{connection.pad_number}."
                    )

        for net_name in self.routed_nets:
            if net_name not in self.nets:
                errors.append(
                    "Routing exists for undefined "
                    f"net {net_name}."
                )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """
        转换为 EDA 中间格式字典。
        """

        return {
            "metadata": {
                "format": "LLM-PCB-EDA-Design",
                "version": "1.0",
                "name": self.name,
                "topology": self.topology,
                "unit": self.unit,
                **self.metadata,
            },
            "board": {
                "width": self.board_width,
                "height": self.board_height,
                "unit": self.unit,
            },
            "components": [
                component.to_dict()
                for component in (
                    self.components.values()
                )
            ],
            "nets": [
                net.to_dict()
                for net in self.nets.values()
            ],
            "routed_nets": [
                routed_net.to_dict()
                for routed_net in (
                    self.routed_nets.values()
                )
            ],
            "statistics": {
                "component_count": len(
                    self.components
                ),
                "net_count": len(
                    self.nets
                ),
                "routed_net_count": len(
                    self.routed_nets
                ),
                "total_routing_length": sum(
                    routed_net.total_length()
                    for routed_net in (
                        self.routed_nets.values()
                    )
                ),
            },
        }

    def show(self) -> None:
        """
        在终端显示设计摘要。
        """

        print("=" * 60)
        print("EDA DESIGN MODEL")
        print("=" * 60)

        print(f"\nName: {self.name}")
        print(f"Topology: {self.topology}")

        print(
            f"Board: {self.board_width} × "
            f"{self.board_height} {self.unit}"
        )

        print("\nComponents:")

        for component in (
            self.components.values()
        ):
            print(
                f"- {component.reference}: "
                f"{component.part_number or component.value}, "
                f"position=("
                f"{component.position.x}, "
                f"{component.position.y}), "
                f"pads={len(component.pads)}"
            )

        print("\nNets:")

        for net in self.nets.values():
            formatted_connections = [
                (
                    f"{connection.reference}."
                    f"{connection.pad_number}"
                )
                for connection in net.connections
            ]

            print(
                f"- {net.name}: "
                + ", ".join(
                    formatted_connections
                )
            )

        print("\nRouting:")

        for routed_net in (
            self.routed_nets.values()
        ):
            print(
                f"- {routed_net.net_name}: "
                f"{len(routed_net.segments)} "
                "segments, "
                f"{routed_net.total_length():.3f} "
                f"{self.unit}"
            )

        print("\nStatistics:")
        print(
            f"- Components: "
            f"{len(self.components)}"
        )
        print(
            f"- Nets: {len(self.nets)}"
        )
        print(
            f"- Routed nets: "
            f"{len(self.routed_nets)}"
        )