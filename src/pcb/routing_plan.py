from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingEndpoint:
    """
    一条连接的端点。
    """

    reference: str
    pin_number: str
    pin_name: str
    x: float
    y: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "pin_number": self.pin_number,
            "pin_name": self.pin_name,
            "x": self.x,
            "y": self.y,
        }


@dataclass
class NetRoutingPlan:
    """
    单个网络的布线计划。
    """

    net_name: str
    endpoints: list[RoutingEndpoint]
    priority: int
    preferred_width: float
    strategy: str
    preferred_layer: str = "Top"
    avoid_nets: list[str] = field(
        default_factory=list
    )
    rule_texts: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "net_name": self.net_name,
            "endpoints": [
                endpoint.to_dict()
                for endpoint in self.endpoints
            ],
            "priority": self.priority,
            "preferred_width": (
                self.preferred_width
            ),
            "strategy": self.strategy,
            "preferred_layer": (
                self.preferred_layer
            ),
            "avoid_nets": self.avoid_nets,
            "rule_texts": self.rule_texts,
        }


class RoutingPlan:
    """
    保存整块 PCB 的全部网络布线计划。
    """

    def __init__(self) -> None:
        self.net_plans: dict[
            str,
            NetRoutingPlan,
        ] = {}

    def add_net_plan(
        self,
        plan: NetRoutingPlan,
    ) -> None:
        if plan.net_name in self.net_plans:
            raise ValueError(
                "Routing plan already exists "
                f"for net: {plan.net_name}"
            )

        self.net_plans[plan.net_name] = plan

    def get_net_plan(
        self,
        net_name: str,
    ) -> NetRoutingPlan:
        if net_name not in self.net_plans:
            raise KeyError(
                f"Routing plan not found: {net_name}"
            )

        return self.net_plans[net_name]

    def get_sorted_plans(
        self,
    ) -> list[NetRoutingPlan]:
        """
        priority 数值越小，布线优先级越高。
        """

        return sorted(
            self.net_plans.values(),
            key=lambda plan: plan.priority,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "nets": [
                plan.to_dict()
                for plan in self.get_sorted_plans()
            ],
            "statistics": {
                "net_count": len(
                    self.net_plans
                )
            },
        }

    def show(self) -> None:
        print("=" * 60)
        print("CONSTRAINT-AWARE ROUTING PLAN")
        print("=" * 60)

        for plan in self.get_sorted_plans():
            print(f"\nNet: {plan.net_name}")
            print(
                f"- Priority: {plan.priority}"
            )
            print(
                "- Preferred width: "
                f"{plan.preferred_width} mm"
            )
            print(
                f"- Strategy: {plan.strategy}"
            )
            print(
                "- Preferred layer: "
                f"{plan.preferred_layer}"
            )

            if plan.avoid_nets:
                print(
                    "- Avoid nets: "
                    + ", ".join(plan.avoid_nets)
                )

            print("- Endpoints:")

            for endpoint in plan.endpoints:
                print(
                    "  "
                    f"{endpoint.reference}."
                    f"{endpoint.pin_name}"
                    f"({endpoint.pin_number}) "
                    f"at ({endpoint.x}, "
                    f"{endpoint.y})"
                )

            if plan.rule_texts:
                print("- Applied rules:")

                for rule_text in plan.rule_texts:
                    print(f"  {rule_text}")

        print("\nStatistics:")
        print(
            f"- Planned nets: "
            f"{len(self.net_plans)}"
        )