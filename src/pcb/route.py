from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoutePoint:
    """
    走线路径上的一个坐标点。
    """

    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
        }


@dataclass
class RouteSegment:
    """
    两个路径点之间的一段直线。
    """

    start: RoutePoint
    end: RoutePoint
    width: float
    layer: str

    def length(self) -> float:
        """
        计算当前线段长度。

        Manhattan Router 只产生水平或垂直线段。
        """

        return (
            abs(self.end.x - self.start.x)
            + abs(self.end.y - self.start.y)
        )

    def is_horizontal(self) -> bool:
        return self.start.y == self.end.y

    def is_vertical(self) -> bool:
        return self.start.x == self.end.x

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "width": self.width,
            "layer": self.layer,
            "length": self.length(),
        }


@dataclass
class RoutedConnection:
    """
    一个网络中两个端点之间的已布线路径。
    """

    source_reference: str
    source_pin: str
    target_reference: str
    target_pin: str
    points: list[RoutePoint]
    segments: list[RouteSegment]

    def total_length(self) -> float:
        return sum(
            segment.length()
            for segment in self.segments
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": {
                "reference": self.source_reference,
                "pin": self.source_pin,
            },
            "target": {
                "reference": self.target_reference,
                "pin": self.target_pin,
            },
            "points": [
                point.to_dict()
                for point in self.points
            ],
            "segments": [
                segment.to_dict()
                for segment in self.segments
            ],
            "total_length": self.total_length(),
        }


@dataclass
class RoutedNet:
    """
    一个已经完成几何布线的网络。
    """

    net_name: str
    priority: int
    preferred_width: float
    preferred_layer: str
    connections: list[RoutedConnection] = field(
        default_factory=list
    )

    def add_connection(
        self,
        connection: RoutedConnection,
    ) -> None:
        self.connections.append(connection)

    def total_length(self) -> float:
        return sum(
            connection.total_length()
            for connection in self.connections
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "net_name": self.net_name,
            "priority": self.priority,
            "preferred_width": self.preferred_width,
            "preferred_layer": self.preferred_layer,
            "connections": [
                connection.to_dict()
                for connection in self.connections
            ],
            "total_length": self.total_length(),
        }


class RoutingResult:
    """
    保存所有网络的几何布线结果。
    """

    def __init__(self) -> None:
        self.routed_nets: dict[str, RoutedNet] = {}

    def add_routed_net(
        self,
        routed_net: RoutedNet,
    ) -> None:
        if routed_net.net_name in self.routed_nets:
            raise ValueError(
                "Routed net already exists: "
                f"{routed_net.net_name}"
            )

        self.routed_nets[
            routed_net.net_name
        ] = routed_net

    def get_routed_net(
        self,
        net_name: str,
    ) -> RoutedNet:
        if net_name not in self.routed_nets:
            raise KeyError(
                f"Routed net not found: {net_name}"
            )

        return self.routed_nets[net_name]

    def total_length(self) -> float:
        return sum(
            routed_net.total_length()
            for routed_net in self.routed_nets.values()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "nets": [
                routed_net.to_dict()
                for routed_net in sorted(
                    self.routed_nets.values(),
                    key=lambda item: item.priority,
                )
            ],
            "statistics": {
                "net_count": len(
                    self.routed_nets
                ),
                "total_length": self.total_length(),
            },
        }

    def show(self) -> None:
        print("=" * 60)
        print("MANHATTAN ROUTING RESULT")
        print("=" * 60)

        routed_nets = sorted(
            self.routed_nets.values(),
            key=lambda item: item.priority,
        )

        for routed_net in routed_nets:
            print(f"\nNet: {routed_net.net_name}")
            print(
                f"- Priority: {routed_net.priority}"
            )
            print(
                "- Width: "
                f"{routed_net.preferred_width} mm"
            )
            print(
                "- Layer: "
                f"{routed_net.preferred_layer}"
            )
            print(
                "- Total length: "
                f"{routed_net.total_length():.2f} mm"
            )

            for connection in routed_net.connections:
                formatted_points = " -> ".join(
                    (
                        f"({point.x:.1f}, "
                        f"{point.y:.1f})"
                    )
                    for point in connection.points
                )

                print(
                    "  "
                    f"{connection.source_reference}."
                    f"{connection.source_pin}"
                    " -> "
                    f"{connection.target_reference}."
                    f"{connection.target_pin}"
                )
                print(
                    f"    Path: {formatted_points}"
                )

        print("\nStatistics:")
        print(
            "- Routed nets: "
            f"{len(self.routed_nets)}"
        )
        print(
            "- Total routing length: "
            f"{self.total_length():.2f} mm"
        )