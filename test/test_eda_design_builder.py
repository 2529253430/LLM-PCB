from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

TEST_DIR = (
    Path(__file__).resolve().parent
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

sys.path.insert(
    0,
    str(TEST_DIR),
)


from src.eda.design_builder import (
    EDADesignBuilder,
)
from test_manhattan_routing import (
    build_test_routing_result,
)
from test_placement_pipeline import (
    build_test_placement,
)
from test_schematic_pipeline import (
    build_test_schematic,
)


def build_complete_eda_design():
    """
    将 Buck 原理图、布局和布线
    转换为完整 EDADesign。
    """

    circuit_graph = (
        build_test_schematic()
    )

    board = build_test_placement()

    routing_result = (
        build_test_routing_result()
    )

    builder = EDADesignBuilder()

    eda_design = builder.build(
        name="Buck_24V_to_5V_3A",
        topology="Buck",
        circuit_graph=circuit_graph,
        board=board,
        routing_result=routing_result,
    )

    return eda_design


def validate_complete_eda_design(
    eda_design,
) -> None:
    """
    验证完整 Buck EDA 模型。
    """

    assert len(
        eda_design.components
    ) == 6

    assert len(
        eda_design.nets
    ) == 5

    assert len(
        eda_design.routed_nets
    ) == 5

    expected_references = {
        "U1",
        "CIN",
        "L1",
        "COUT",
        "R1",
        "R2",
    }

    assert set(
        eda_design.components.keys()
    ) == expected_references

    expected_nets = {
        "VIN",
        "SW",
        "VOUT",
        "FB",
        "GND",
    }

    assert set(
        eda_design.nets.keys()
    ) == expected_nets

    u1 = eda_design.get_component(
        "U1"
    )

    assert u1.part_number == (
        "TPS5430DDA"
    )

    assert u1.footprint_name == (
        "SOIC-8-PowerPAD-DDA"
    )

    assert len(u1.pads) == 9

    assert u1.get_pad("6").name == "VIN"
    assert u1.get_pad("7").name == "PH"
    assert u1.get_pad("3").name == "VSENSE"
    assert u1.get_pad("5").name == "GND"

    assert (
        u1.get_pad("6").position.x,
        u1.get_pad("6").position.y,
    ) == (
        34.7,
        39.365,
    )

    assert (
        u1.get_pad("7").position.x,
        u1.get_pad("7").position.y,
    ) == (
        34.7,
        40.635,
    )

    for reference in (
        "CIN",
        "L1",
        "COUT",
        "R1",
        "R2",
    ):
        component = (
            eda_design.get_component(
                reference
            )
        )

        assert len(
            component.pads
        ) == 2

    vin_net = eda_design.get_net(
        "VIN"
    )

    vin_connections = {
        (
            connection.reference,
            connection.pad_number,
        )
        for connection in (
            vin_net.connections
        )
    }

    assert vin_connections == {
        (
            "U1",
            "6",
        ),
        (
            "CIN",
            "1",
        ),
    }

    sw_net = eda_design.get_net(
        "SW"
    )

    sw_connections = {
        (
            connection.reference,
            connection.pad_number,
        )
        for connection in (
            sw_net.connections
        )
    }

    assert sw_connections == {
        (
            "U1",
            "7",
        ),
        (
            "L1",
            "1",
        ),
    }

    fb_net = eda_design.get_net(
        "FB"
    )

    fb_connections = {
        (
            connection.reference,
            connection.pad_number,
        )
        for connection in (
            fb_net.connections
        )
    }

    assert fb_connections == {
        (
            "U1",
            "3",
        ),
        (
            "R1",
            "2",
        ),
        (
            "R2",
            "1",
        ),
    }

    gnd_net = eda_design.get_net(
        "GND"
    )

    gnd_connections = {
        (
            connection.reference,
            connection.pad_number,
        )
        for connection in (
            gnd_net.connections
        )
    }

    assert gnd_connections == {
        (
            "U1",
            "5",
        ),
        (
            "CIN",
            "2",
        ),
        (
            "COUT",
            "2",
        ),
        (
            "R2",
            "2",
        ),
    }

    errors = eda_design.validate()

    assert not errors, errors

    document = eda_design.to_dict()

    assert document[
        "metadata"
    ][
        "format"
    ] == "LLM-PCB-EDA-Design"

    assert document[
        "metadata"
    ][
        "target_import"
    ] == "Altium Designer"

    assert document[
        "statistics"
    ][
        "component_count"
    ] == 6

    assert document[
        "statistics"
    ][
        "net_count"
    ] == 5

    assert document[
        "statistics"
    ][
        "routed_net_count"
    ] == 5

    assert document[
        "statistics"
    ][
        "total_routing_length"
    ] > 0

    print(
        "Complete EDA design builder "
        "validation passed."
    )


if __name__ == "__main__":
    design = (
        build_complete_eda_design()
    )

    design.show()

    print()

    validate_complete_eda_design(
        design
    )