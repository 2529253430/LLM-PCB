from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))


from src.schematic.schematic_generator import (
    SchematicGenerator,
)
from test_design_pipeline import (
    build_test_design,
)


def build_test_schematic():
    """
    先生成 Constraint Graph，
    再生成带真实物理引脚编号的 Buck 原理图。
    """

    constraint_graph = build_test_design()

    generator = SchematicGenerator()

    circuit_graph = generator.generate_buck(
        constraint_graph=constraint_graph
    )

    return circuit_graph


def validate_schematic() -> None:
    """
    验证 Buck 原理图中的元件、网络和物理引脚编号。
    """

    circuit_graph = build_test_schematic()

    components = {
        reference
        for reference, _ in circuit_graph.get_components()
    }

    expected_components = {
        "U1",
        "CIN",
        "L1",
        "COUT",
        "R1",
        "R2",
    }

    assert components == expected_components, (
        "Unexpected schematic components: "
        f"{components}"
    )

    nets = {
        net_data["name"]
        for _, net_data in circuit_graph.get_nets()
    }

    expected_nets = {
        "VIN",
        "SW",
        "VOUT",
        "FB",
        "GND",
    }

    assert nets == expected_nets, (
        f"Unexpected schematic nets: {nets}"
    )

    vin_connections = (
        circuit_graph.get_net_connections("VIN")
    )

    sw_connections = (
        circuit_graph.get_net_connections("SW")
    )

    fb_connections = (
        circuit_graph.get_net_connections("FB")
    )

    gnd_connections = (
        circuit_graph.get_net_connections("GND")
    )

    u1_vin = next(
        connection
        for connection in vin_connections
        if connection["reference"] == "U1"
    )

    u1_sw = next(
        connection
        for connection in sw_connections
        if connection["reference"] == "U1"
    )

    u1_fb = next(
        connection
        for connection in fb_connections
        if connection["reference"] == "U1"
    )

    u1_gnd = next(
        connection
        for connection in gnd_connections
        if connection["reference"] == "U1"
    )

    assert u1_vin["pin_number"] == "6"
    assert u1_vin["pin_name"] == "VIN"

    assert u1_sw["pin_number"] == "7"
    assert u1_sw["pin_name"] == "SW"

    assert u1_fb["pin_number"] == "3"
    assert u1_fb["pin_name"] == "FB"

    assert u1_gnd["pin_number"] == "5"
    assert u1_gnd["pin_name"] == "GND"

    assert len(circuit_graph.get_components()) == 6
    assert len(circuit_graph.get_pins()) == 14
    assert len(circuit_graph.get_nets()) == 5

    print("Schematic validation passed.")


if __name__ == "__main__":
    schematic = build_test_schematic()

    schematic.show()

    print()
    validate_schematic()