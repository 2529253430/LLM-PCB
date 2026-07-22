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


from src.export.kicad_pcb_exporter import (
    KiCadPCBExporter,
)
from test_eda_design_builder import (
    build_complete_eda_design,
)


def validate_parentheses(
    content: str,
) -> None:
    """
    检查 S-expression 括号是否平衡。

    字符串内部的括号不会参与统计。
    """

    depth = 0
    in_string = False
    escaped = False

    for character in content:
        if escaped:
            escaped = False
            continue

        if (
            character == "\\"
            and in_string
        ):
            escaped = True
            continue

        if character == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if character == "(":
            depth += 1

        elif character == ")":
            depth -= 1

            if depth < 0:
                raise AssertionError(
                    "Unexpected closing "
                    "parenthesis."
                )

    assert not in_string, (
        "Unterminated string in KiCad file."
    )

    assert depth == 0, (
        "Unbalanced parentheses "
        "in KiCad file."
    )


def test_kicad_pcb_exporter() -> Path:
    """
    导出完整 Buck PCB，
    并验证关键文件内容。
    """

    design = (
        build_complete_eda_design()
    )

    output_path = (
        PROJECT_ROOT
        / "output"
        / "kicad"
        / "Buck_24V_to_5V_3A.kicad_pcb"
    )

    exporter = KiCadPCBExporter()

    exported_path = exporter.export(
        design=design,
        output_path=output_path,
    )

    assert exported_path.exists()

    assert exported_path.suffix == (
        ".kicad_pcb"
    )

    content = (
        exported_path.read_text(
            encoding="utf-8"
        )
    )

    validate_parentheses(
        content
    )

    assert content.startswith(
        "(kicad_pcb "
    )

    assert (
        '(generator "llm-pcb")'
        in content
    )

    assert (
        '(layer "Edge.Cuts")'
        in content
    )

    for net_name in (
        "VIN",
        "SW",
        "VOUT",
        "FB",
        "GND",
    ):
        assert (
            f'"{net_name}"'
            in content
        )

    assert content.count(
        "  (footprint "
    ) == len(
        design.components
    )

    expected_pad_count = sum(
        len(component.pads)
        for component in (
            design.components.values()
        )
    )

    assert content.count(
        "    (pad "
    ) == expected_pad_count

    expected_segment_count = sum(
        len(routed_net.segments)
        for routed_net in (
            design.routed_nets.values()
        )
    )

    assert content.count(
        "  (segment"
    ) == expected_segment_count

    assert '"U1"' in content

    assert (
        '"TPS5430DDA"'
        in content
    )

    assert (
        "(net 1 "
        in content
    )

    print(
        "KiCad PCB exporter "
        "validation passed."
    )

    print(
        f"Generated file: "
        f"{exported_path}"
    )

    print(
        f"Components: "
        f"{len(design.components)}"
    )

    print(
        f"Pads: "
        f"{expected_pad_count}"
    )

    print(
        f"Segments: "
        f"{expected_segment_count}"
    )

    

if __name__ == "__main__":
    test_kicad_pcb_exporter()