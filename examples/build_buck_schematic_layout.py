from __future__ import annotations

import json
from pathlib import Path

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def main() -> None:
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
    )

    selected_ic = BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
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

    output_path = Path(
        "output/buck_schematic_layout.json"
    )
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            layout.to_dict(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Schematic: {layout.design_name}")
    print(f"Symbols: {len(layout.symbols)}")
    print(f"Pins: {len(layout.pins)}")
    print(f"Wires: {len(layout.wires)}")
    print(f"Junctions: {len(layout.junctions)}")
    print(f"Labels: {len(layout.labels)}")

    for net_name in sorted(
        {
            wire.net_name
            for wire in layout.wires
        }
    ):
        print(
            f"- {net_name}: "
            f"{len(layout.wires_for_net(net_name))} wires"
        )

    print(
        f"Layout written to: {output_path.resolve()}"
    )


if __name__ == "__main__":
    main()
