from __future__ import annotations

import pytest

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import (
    BuckSchematicLayoutEngine,
    Point,
    SchematicLayoutError,
)


def _schematic():
    design_input = BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
    )

    ic = BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        switch_current_limit_a=5.5,
    )

    result = BuckDesignEngine().design(
        design_input,
        ic,
    )

    return BuckSchematicBuilder().build(
        design_input,
        ic,
        result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )


def test_layout_contains_all_symbols() -> None:
    schematic = _schematic()

    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    assert set(layout.symbols) == {
        component.reference
        for component in schematic.components
    }


def test_layout_contains_all_pin_endpoints() -> None:
    schematic = _schematic()

    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    expected_pin_count = sum(
        len(component.pins)
        for component in schematic.components
    )

    assert len(layout.pins) == expected_pin_count


def test_every_net_has_visible_wires() -> None:
    schematic = _schematic()

    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    for net in schematic.nets:
        assert layout.wires_for_net(net.name)


def test_all_wires_are_orthogonal() -> None:
    layout = BuckSchematicLayoutEngine().layout(
        _schematic()
    )

    for wire in layout.wires:
        horizontal = wire.start.y == wire.end.y
        vertical = wire.start.x == wire.end.x

        assert horizontal or vertical


def test_enable_and_vin_share_one_net_layout() -> None:
    schematic = _schematic()

    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    vin_net = schematic.get_net("VIN")

    vin_connections = {
        (
            connection.component_reference,
            connection.pin_number,
        )
        for connection in vin_net.connections
    }

    assert ("U1", "1") in vin_connections
    assert ("U1", "5") in vin_connections
    assert layout.wires_for_net("VIN")


def test_custom_symbol_position_is_supported() -> None:
    schematic = _schematic()

    layout = BuckSchematicLayoutEngine().layout(
        schematic,
        symbol_positions={
            "U1": Point(100.0, 80.0),
        },
    )

    assert layout.get_symbol("U1").position == Point(
        99.06,
        78.74,
    )


def test_missing_position_is_rejected() -> None:
    schematic = _schematic()
    engine = BuckSchematicLayoutEngine()

    engine.DEFAULT_POSITIONS = {
        key: value
        for key, value in engine.DEFAULT_POSITIONS.items()
        if key != "U1"
    }

    with pytest.raises(
        SchematicLayoutError,
        match="U1",
    ):
        engine.layout(schematic)


def test_layout_can_be_serialized() -> None:
    schematic = _schematic()

    layout = BuckSchematicLayoutEngine().layout(
        schematic
    )

    payload = layout.to_dict()

    assert payload["design_name"] == schematic.name
    assert payload["symbols"]
    assert payload["pins"]
    assert payload["wires"]
    assert payload["junctions"]
    assert payload["labels"]
