from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.export.kicad_project_exporter import (
    KiCadProjectExporter,
    KiCadProjectMetadata,
)
from src.schematic.buck_builder import (
    BuckSchematicBuilder,
)
from src.schematic.layout import (
    BuckSchematicLayoutEngine,
)


def object_to_dict(value: Any) -> Dict[str, Any]:
    """
    Convert a design result object into JSON-compatible metadata.

    Supports:
    - dataclass objects;
    - normal Python objects with __dict__;
    - primitive values;
    - lists, tuples and dictionaries.

    This avoids assuming specific BuckDesignResult field names.
    """

    if is_dataclass(value):
        raw_data = asdict(value)
    elif hasattr(value, "__dict__"):
        raw_data = vars(value)
    else:
        return {
            "value": make_json_compatible(value),
        }

    return {
        str(key): make_json_compatible(item)
        for key, item in raw_data.items()
        if not str(key).startswith("_")
    }


def make_json_compatible(value: Any) -> Any:
    """Convert nested values into JSON-compatible values."""

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value):
        return {
            str(key): make_json_compatible(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            str(key): make_json_compatible(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            make_json_compatible(item)
            for item in value
        ]

    if hasattr(value, "__dict__"):
        return {
            str(key): make_json_compatible(item)
            for key, item in vars(value).items()
            if not str(key).startswith("_")
        }

    return str(value)


def main() -> None:
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
        output_voltage_ripple_v=0.05,
        input_voltage_ripple_v=0.20,
    )

    selected_ic = BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        minimum_on_time_s=80e-9,
        maximum_duty_cycle=0.90,
        switch_current_limit_a=5.5,
    )

    result = BuckDesignEngine().design(
        design_input,
        selected_ic,
    )

    schematic = BuckSchematicBuilder().build(
        design_input,
        selected_ic,
        result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )

    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    pcb_source = Path(
        "output/kicad/"
        "Buck_24V_to_5V_3A.kicad_pcb"
    )

    if not pcb_source.exists():
        raise FileNotFoundError(
            "找不到已经生成的 PCB 文件："
            f"{pcb_source.resolve()}\n"
            "请先运行 PCB 导出流程，或者检查 PCB 文件名。"
        )

    metadata = KiCadProjectMetadata(
        topology="buck",
        requirements={
            "input_voltage_min_v": (
                design_input.input_voltage_min_v
            ),
            "input_voltage_max_v": (
                design_input.input_voltage_max_v
            ),
            "output_voltage_v": (
                design_input.output_voltage_v
            ),
            "output_current_a": (
                design_input.output_current_a
            ),
            "output_voltage_ripple_v": (
                design_input.output_voltage_ripple_v
            ),
            "input_voltage_ripple_v": (
                design_input.input_voltage_ripple_v
            ),
        },
        selected_component={
            "part_number": (
                selected_ic.part_number
            ),
            "switching_frequency_hz": (
                selected_ic.switching_frequency_hz
            ),
            "feedback_reference_voltage_v": (
                selected_ic.feedback_reference_voltage_v
            ),
            "minimum_on_time_s": (
                selected_ic.minimum_on_time_s
            ),
            "maximum_duty_cycle": (
                selected_ic.maximum_duty_cycle
            ),
            "switch_current_limit_a": (
                selected_ic.switch_current_limit_a
            ),
        },
        calculations=object_to_dict(result),
    )

    project = KiCadProjectExporter().export(
        project_name="Buck_24V_to_5V_3A",
        schematic=schematic,
        layout=layout,
        pcb_source_path=pcb_source,
        output_root="output/projects",
        metadata=metadata,
    )

    print()
    print("KiCad project generated successfully.")
    print(f"Directory:  {project.directory.resolve()}")
    print(f"Project:    {project.project_file.name}")
    print(f"Schematic:  {project.schematic_file.name}")
    print(f"PCB:        {project.pcb_file.name}")
    print(f"Metadata:   {project.metadata_file.name}")
    print(f"Validation: {project.validation_file.name}")
    print()


if __name__ == "__main__":
    main()