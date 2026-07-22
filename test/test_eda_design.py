from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


from src.eda.design import (
    EDAComponent,
    EDADesign,
    EDAPad,
    EDAPoint,
    EDARoutedNet,
    EDARouteSegment,
)


def build_test_eda_design() -> EDADesign:
    """
    创建一个最小 Buck EDA 设计，
    用于验证新数据模型。
    """

    design = EDADesign(
        name="Buck_24V_to_5V",
        topology="Buck",
        board_width=100.0,
        board_height=80.0,
        unit="mm",
    )

    u1 = EDAComponent(
        reference="U1",
        part_number="TPS5430DDA",
        component_type="Controller",
        symbol_name="TPS5430",
        footprint_name=(
            "SOIC-8-PowerPAD-DDA"
        ),
        position=EDAPoint(
            x=32.0,
            y=40.0,
        ),
        rotation=0.0,
        manufacturer=(
            "Texas Instruments"
        ),
    )

    u1.add_pad(
        EDAPad(
            number="6",
            name="VIN",
            position=EDAPoint(
                x=34.7,
                y=39.365,
            ),
            width=0.6,
            height=1.6,
        )
    )

    u1.add_pad(
        EDAPad(
            number="7",
            name="SW",
            position=EDAPoint(
                x=34.7,
                y=40.635,
            ),
            width=0.6,
            height=1.6,
        )
    )

    design.add_component(u1)

    cin = EDAComponent(
        reference="CIN",
        part_number="",
        component_type=(
            "Input Capacitor"
        ),
        symbol_name="C",
        footprint_name="C_1210",
        position=EDAPoint(
            x=15.0,
            y=40.0,
        ),
        value="22uF",
    )

    cin.add_pad(
        EDAPad(
            number="1",
            name="POS",
            position=EDAPoint(
                x=11.0,
                y=40.0,
            ),
            width=2.0,
            height=2.0,
        )
    )

    cin.add_pad(
        EDAPad(
            number="2",
            name="NEG",
            position=EDAPoint(
                x=19.0,
                y=40.0,
            ),
            width=2.0,
            height=2.0,
        )
    )

    design.add_component(cin)

    design.connect(
        net_name="VIN",
        reference="U1",
        pad_number="6",
    )

    design.connect(
        net_name="VIN",
        reference="CIN",
        pad_number="1",
    )

    vin_route = EDARoutedNet(
        net_name="VIN"
    )

    vin_route.add_segment(
        EDARouteSegment(
            start=EDAPoint(
                x=11.0,
                y=40.0,
            ),
            end=EDAPoint(
                x=34.7,
                y=40.0,
            ),
            width=2.0,
            layer="F.Cu",
        )
    )

    vin_route.add_segment(
        EDARouteSegment(
            start=EDAPoint(
                x=34.7,
                y=40.0,
            ),
            end=EDAPoint(
                x=34.7,
                y=39.365,
            ),
            width=2.0,
            layer="F.Cu",
        )
    )

    design.add_routed_net(
        vin_route
    )

    return design


def validate_test_eda_design(
    design: EDADesign,
) -> None:
    """
    验证 EDA Design Model 的关键功能。
    """

    assert len(design.components) == 2
    assert len(design.nets) == 1
    assert len(design.routed_nets) == 1

    u1 = design.get_component("U1")
    cin = design.get_component("CIN")

    assert u1.part_number == (
        "TPS5430DDA"
    )

    assert u1.get_pad("6").name == "VIN"
    assert u1.get_pad("7").name == "SW"

    assert cin.get_pad("1").name == "POS"

    vin_net = design.get_net("VIN")

    assert len(
        vin_net.connections
    ) == 2

    errors = design.validate()

    assert not errors, errors

    document = design.to_dict()

    assert document["metadata"][
        "format"
    ] == "LLM-PCB-EDA-Design"

    assert document["statistics"][
        "component_count"
    ] == 2

    assert document["statistics"][
        "net_count"
    ] == 1

    assert document["statistics"][
        "routed_net_count"
    ] == 1

    assert document["statistics"][
        "total_routing_length"
    ] > 0

    print(
        "EDA design model validation passed."
    )


if __name__ == "__main__":
    test_design = (
        build_test_eda_design()
    )

    test_design.show()

    print()

    validate_test_eda_design(
        test_design
    )