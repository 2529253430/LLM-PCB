from pathlib import Path
import sys

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

from src.database.component_instance import (
    ComponentInstance,
)


def test_zero_degree_rotation() -> None:
    """
    测试旋转角度为 0° 时的 Pad 坐标。
    """

    u1 = ComponentInstance(
        reference="U1",
        part_number="TPS5430DDA",
        x=32.0,
        y=40.0,
        rotation=0.0,
    )

    pad_7 = u1.get_pad_position("7")

    assert pad_7.x == 34.7
    assert pad_7.y == 40.635

    print(
        "Pad 7 at 0 degrees:",
        pad_7.to_dict(),
    )


def test_logical_role_mapping() -> None:
    """
    测试逻辑网络角色到真实 Pad 的映射。
    """

    u1 = ComponentInstance(
        reference="U1",
        part_number="TPS5430DDA",
        x=32.0,
        y=40.0,
    )

    vin_pads = u1.get_pads_by_logical_role(
        "VIN"
    )

    sw_pads = u1.get_pads_by_logical_role(
        "SW"
    )

    fb_pads = u1.get_pads_by_logical_role(
        "FB"
    )

    gnd_pads = u1.get_pads_by_logical_role(
        "GND"
    )

    assert [
        pad.pad_number
        for pad in vin_pads
    ] == ["6"]

    assert [
        pad.pad_number
        for pad in sw_pads
    ] == ["7", "8"]

    assert [
        pad.pad_number
        for pad in fb_pads
    ] == ["3"]

    assert [
        pad.pad_number
        for pad in gnd_pads
    ] == ["5", "9"]

    print(
        "VIN pads:",
        [
            pad.to_dict()
            for pad in vin_pads
        ],
    )

    print(
        "SW pads:",
        [
            pad.to_dict()
            for pad in sw_pads
        ],
    )

    print(
        "FB pads:",
        [
            pad.to_dict()
            for pad in fb_pads
        ],
    )

    print(
        "GND pads:",
        [
            pad.to_dict()
            for pad in gnd_pads
        ],
    )


def test_ninety_degree_rotation() -> None:
    """
    测试旋转 90° 后的焊盘坐标。
    """

    u1 = ComponentInstance(
        reference="U1",
        part_number="TPS5430DDA",
        x=32.0,
        y=40.0,
        rotation=90.0,
    )

    pad_7 = u1.get_pad_position("7")

    # 原局部坐标：
    # (2.7, 0.635)
    #
    # 旋转 90°：
    # (-0.635, 2.7)
    #
    # 加上元件中心：
    # (31.365, 42.7)

    assert pad_7.x == 31.365
    assert pad_7.y == 42.7

    print(
        "Pad 7 at 90 degrees:",
        pad_7.to_dict(),
    )


def test_all_pads() -> None:
    """
    检查器件包含 9 个 Pad。
    """

    u1 = ComponentInstance(
        reference="U1",
        part_number="TPS5430DDA",
        x=32.0,
        y=40.0,
    )

    all_pads = u1.get_all_pad_positions()

    assert len(all_pads) == 9

    print(
        "All pad count:",
        len(all_pads),
    )


if __name__ == "__main__":
    print("=" * 60)
    print("COMPONENT INSTANCE VALIDATION")
    print("=" * 60)

    test_zero_degree_rotation()
    print()

    test_logical_role_mapping()
    print()

    test_ninety_degree_rotation()
    print()

    test_all_pads()

    print()
    print(
        "Component instance validation passed."
    )