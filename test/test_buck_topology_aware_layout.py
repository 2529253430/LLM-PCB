from __future__ import annotations

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine


def _design():
    design_input = BuckDesignInput(18.0, 24.0, 5.0, 3.0)
    ic = BuckICParameters("EX36S4", 0.8, 500_000.0, 5.5)
    result = BuckDesignEngine().design(design_input, ic)
    return BuckSchematicBuilder().build(design_input, ic, result)


def test_power_stage_is_left_to_right() -> None:
    layout = BuckSchematicLayoutEngine().layout(_design())

    x = {ref: layout.get_symbol(ref).position.x for ref in layout.symbols}
    assert x["J1"] < x["CIN"] < x["U1"] < x["L1"]
    assert x["L1"] < x["COUT"] < x["J2"]


def test_feedback_divider_is_vertical() -> None:
    layout = BuckSchematicLayoutEngine().layout(_design())

    r1 = layout.get_symbol("R1").position
    r2 = layout.get_symbol("R2").position
    assert r1.x == r2.x
    assert r1.y > r2.y


def test_main_power_nets_use_power_lane() -> None:
    engine = BuckSchematicLayoutEngine()
    layout = engine.layout(_design())
    expected_y = round(engine.POWER_PATH_Y / engine.grid_mm) * engine.grid_mm

    for net_name in ("VIN", "SW", "VOUT"):
        assert any(
            wire.start.y == wire.end.y == expected_y
            for wire in layout.wires_for_net(net_name)
        )


def test_ground_uses_separate_return_lane() -> None:
    engine = BuckSchematicLayoutEngine()
    layout = engine.layout(_design())
    expected_y = round(engine.GROUND_Y / engine.grid_mm) * engine.grid_mm

    assert any(
        wire.start.y == wire.end.y == expected_y
        for wire in layout.wires_for_net("GND")
    )
    assert expected_y != round(
        engine.POWER_PATH_Y / engine.grid_mm
    ) * engine.grid_mm


def test_layout_metadata_identifies_phase16e() -> None:
    layout = BuckSchematicLayoutEngine().layout(_design())

    assert layout.metadata["layout_phase"] == "16E"
    assert layout.metadata["layout_strategy"] == "topology_aware_signal_flow"
