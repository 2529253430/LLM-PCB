from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


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


EXPECTED_REFERENCES = {
    "U1",
    "CIN",
    "L1",
    "COUT",
    "R1",
    "R2",
}

EXPECTED_NETS = {
    "VIN",
    "SW",
    "VOUT",
    "FB",
    "GND",
}


def validate_parentheses(
    content: str,
) -> None:
    """
    验证 KiCad S-expression 括号是否平衡。

    字符串中的括号不参与统计。
    """

    depth = 0
    in_string = False
    escaped = False

    for index, character in enumerate(
        content
    ):
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
            continue

        if character == ")":
            depth -= 1

            if depth < 0:
                raise AssertionError(
                    "Unexpected closing parenthesis "
                    f"at character {index}."
                )

    if in_string:
        raise AssertionError(
            "The KiCad PCB file contains "
            "an unterminated string."
        )

    if depth != 0:
        raise AssertionError(
            "The KiCad PCB file contains "
            f"unbalanced parentheses: depth={depth}."
        )


def find_kicad_cli() -> Path | None:
    """
    查找 kicad-cli。

    首先检查 PATH，然后检查 Windows 中
    常见的 KiCad 安装目录。
    """

    executable_name = (
        "kicad-cli.exe"
        if sys.platform == "win32"
        else "kicad-cli"
    )

    path_result = shutil.which(
        executable_name
    )

    if path_result:
        return Path(path_result)

    if sys.platform != "win32":
        return None

    program_files_candidates = [
        Path("C:/Program Files/KiCad"),
        Path("C:/Program Files (x86)/KiCad"),
    ]

    version_directories = [
        "10.0",
        "9.0",
        "8.0",
        "7.0",
    ]

    for base_directory in (
        program_files_candidates
    ):
        for version in version_directories:
            candidates = [
                (
                    base_directory
                    / version
                    / "bin"
                    / "kicad-cli.exe"
                ),
                (
                    base_directory
                    / version
                    / "kicad-cli.exe"
                ),
            ]

            for candidate in candidates:
                if candidate.is_file():
                    return candidate

    return None


def run_command(
    command: list[str],
    timeout_seconds: int = 120,
) -> subprocess.CompletedProcess[str]:
    """
    执行外部命令并返回结果。
    """

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )

    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            "External command timed out: "
            + " ".join(command)
        ) from error

    except OSError as error:
        raise RuntimeError(
            "Failed to start external command: "
            + " ".join(command)
        ) from error


def validate_kicad_cli_version(
    kicad_cli: Path,
) -> str:
    """
    调用 kicad-cli version，确认命令可运行。
    """

    result = run_command(
        [
            str(kicad_cli),
            "version",
        ]
    )

    if result.returncode != 0:
        details = (
            result.stderr.strip()
            or result.stdout.strip()
            or "No diagnostic output."
        )

        raise RuntimeError(
            "kicad-cli version failed.\n"
            f"Exit code: {result.returncode}\n"
            f"Details: {details}"
        )

    version_text = result.stdout.strip()

    if not version_text:
        version_text = "Unknown version"

    return version_text


def run_kicad_drc(
    kicad_cli: Path,
    board_path: Path,
    report_path: Path,
) -> subprocess.CompletedProcess[str]:
    """
    使用 KiCad 官方 CLI 读取 PCB 并执行 DRC。

    这里不使用 --exit-code-violations，
    因为当前阶段的目标是验证文件能够被 KiCad
    正确解析，而不是要求所有工程规则立即通过。
    """

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        str(kicad_cli),
        "pcb",
        "drc",
        "--output",
        str(report_path),
        str(board_path),
    ]

    result = run_command(
        command
    )

    if result.returncode != 0:
        details = "\n".join(
            part
            for part in [
                result.stdout.strip(),
                result.stderr.strip(),
            ]
            if part
        )

        if not details:
            details = "No diagnostic output."

        raise RuntimeError(
            "KiCad failed to parse or check "
            "the generated PCB.\n"
            f"Exit code: {result.returncode}\n"
            f"Command: {' '.join(command)}\n"
            f"Details:\n{details}"
        )

    if not report_path.exists():
        raise AssertionError(
            "KiCad completed without creating "
            f"the DRC report: {report_path}"
        )

    return result


def validate_static_board_content(
    board_path: Path,
    expected_component_count: int,
    expected_pad_count: int,
    expected_segment_count: int,
) -> None:
    """
    在调用 KiCad 前执行静态结构检查。
    """

    if not board_path.exists():
        raise AssertionError(
            f"Generated board does not exist: "
            f"{board_path}"
        )

    content = board_path.read_text(
        encoding="utf-8"
    )

    if not content.strip():
        raise AssertionError(
            "Generated KiCad PCB file is empty."
        )

    validate_parentheses(
        content
    )

    if not content.startswith(
        "(kicad_pcb "
    ):
        raise AssertionError(
            "The file does not start with "
            "a kicad_pcb root expression."
        )

    required_sections = [
        "(general",
        "(layers",
        "(setup",
        "(net 0",
        '(layer "Edge.Cuts")',
    ]

    for section in required_sections:
        if section not in content:
            raise AssertionError(
                "Missing required KiCad PCB "
                f"section: {section}"
            )

    actual_component_count = (
        content.count("  (footprint ")
    )

    if (
        actual_component_count
        != expected_component_count
    ):
        raise AssertionError(
            "Unexpected footprint count: "
            f"expected={expected_component_count}, "
            f"actual={actual_component_count}"
        )

    actual_pad_count = content.count(
        "    (pad "
    )

    if actual_pad_count != expected_pad_count:
        raise AssertionError(
            "Unexpected pad count: "
            f"expected={expected_pad_count}, "
            f"actual={actual_pad_count}"
        )

    actual_segment_count = content.count(
        "  (segment"
    )

    if (
        actual_segment_count
        != expected_segment_count
    ):
        raise AssertionError(
            "Unexpected routed segment count: "
            f"expected={expected_segment_count}, "
            f"actual={actual_segment_count}"
        )

    for reference in sorted(
        EXPECTED_REFERENCES
    ):
        reference_expression = (
            f'"{reference}"'
        )

        if reference_expression not in content:
            raise AssertionError(
                "Missing component reference "
                f"in KiCad PCB: {reference}"
            )

    for net_name in sorted(
        EXPECTED_NETS
    ):
        net_expression = (
            f'"{net_name}"'
        )

        if net_expression not in content:
            raise AssertionError(
                "Missing net in KiCad PCB: "
                f"{net_name}"
            )

    edge_count = content.count(
        "  (gr_line"
    )

    if edge_count != 4:
        raise AssertionError(
            "The rectangular board should "
            "contain exactly four Edge.Cuts "
            f"lines, but found {edge_count}."
        )


def run_kicad_integration_test() -> Path:
    """
    生成 PCB 并执行完整 KiCad 集成验证。
    """

    print("=" * 60)
    print("KICAD PCB INTEGRATION TEST")
    print("=" * 60)

    design = (
        build_complete_eda_design()
    )

    output_directory = (
        PROJECT_ROOT
        / "output"
        / "kicad"
    )

    board_path = (
        output_directory
        / "Buck_24V_to_5V_3A.kicad_pcb"
    )

    report_path = (
        output_directory
        / "Buck_24V_to_5V_3A-drc.rpt"
    )

    exporter = KiCadPCBExporter()

    exported_path = exporter.export(
        design=design,
        output_path=board_path,
    )

    expected_component_count = len(
        design.components
    )

    expected_pad_count = sum(
        len(component.pads)
        for component in (
            design.components.values()
        )
    )

    expected_segment_count = sum(
        len(routed_net.segments)
        for routed_net in (
            design.routed_nets.values()
        )
    )

    validate_static_board_content(
        board_path=exported_path,
        expected_component_count=(
            expected_component_count
        ),
        expected_pad_count=(
            expected_pad_count
        ),
        expected_segment_count=(
            expected_segment_count
        ),
    )

    print()
    print("Static file validation passed.")
    print(f"Board file: {exported_path}")
    print(
        "Components: "
        f"{expected_component_count}"
    )
    print(
        "Pads: "
        f"{expected_pad_count}"
    )
    print(
        "Segments: "
        f"{expected_segment_count}"
    )

    kicad_cli = find_kicad_cli()

    if kicad_cli is None:
        print()
        print(
            "kicad-cli was not found."
        )
        print(
            "Static validation passed, but "
            "automatic KiCad parsing was skipped."
        )
        print(
            "Open the generated file manually "
            "in KiCad PCB Editor."
        )

        return exported_path

    version = validate_kicad_cli_version(
        kicad_cli
    )

    print()
    print(f"KiCad CLI: {kicad_cli}")
    print(f"KiCad version: {version}")

    run_kicad_drc(
        kicad_cli=kicad_cli,
        board_path=exported_path,
        report_path=report_path,
    )

    print()
    print(
        "KiCad successfully parsed "
        "the generated PCB."
    )
    print(f"DRC report: {report_path}")

    return exported_path


if __name__ == "__main__":
    final_board_path = (
        run_kicad_integration_test()
    )

    print()
    print(
        "KiCad integration validation passed."
    )
    print(
        f"Final board: {final_board_path}"
    )