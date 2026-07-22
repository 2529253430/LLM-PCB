from __future__ import annotations

import pytest

from src.design.buck_engine import (
    BuckDesignEngine,
    BuckDesignInput,
    BuckICParameters,
)
from src.schematic.buck_builder import (
    BuckSchematicBuilder,
    BuckSymbolMapping,
)


def _design_input() -> BuckDesignInput:
    return BuckDesignInput(
        input_voltage_min_v=18.0,
        input_voltage_max_v=24.0,
        output_voltage_v=5.0,
        output_current_a=3.0,
    )


def _ic() -> BuckICParameters:
    return BuckICParameters(
        part_number="EX36S4",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
        switch_current_limit_a=5.5,
    )


def _build():
    design_input = _design_input()
    ic = _ic()
    result = BuckDesignEngine().design(design_input, ic)

    schematic = BuckSchematicBuilder().build(
        design_input,
        ic,
        result,
        footprint_name="Package_SO:SOIC-8_EP",
        manufacturer="Example Semiconductor",
    )

    return schematic


def test_builder_creates_expected_components() -> None:
    schematic = _build()

    references = {
        component.reference
        for component in schematic.components
    }

    assert {
        "J1",
        "J2",
        "U1",
        "CIN",
        "L1",
        "COUT",
        "R1",
        "R2",
        "CBOOT",
    }.issubset(references)


def test_builder_creates_expected_nets() -> None:
    schematic = _build()

    net_names = {net.name for net in schematic.nets}

    assert {
        "VIN",
        "SW",
        "VOUT",
        "FB",
        "GND",
        "BOOT",
    } == net_names

    assert "EN" not in net_names


def test_enable_pin_is_tied_to_vin() -> None:
    schematic = _build()
    vin = schematic.get_net("VIN")

    connections = {
        (
            connection.component_reference,
            connection.pin_number,
        )
        for connection in vin.connections
    }

    assert ("J1", "1") in connections
    assert ("U1", "1") in connections
    assert ("U1", "5") in connections


def test_feedback_net_connects_divider_and_ic() -> None:
    schematic = _build()
    feedback = schematic.get_net("FB")

    connections = {
        (
            connection.component_reference,
            connection.pin_number,
        )
        for connection in feedback.connections
    }

    assert ("R1", "2") in connections
    assert ("R2", "1") in connections
    assert ("U1", "4") in connections


def test_schematic_validates() -> None:
    schematic = _build()
    schematic.validate()


def test_result_part_number_must_match_ic() -> None:
    design_input = _design_input()
    ic = _ic()
    result = BuckDesignEngine().design(design_input, ic)

    different_ic = BuckICParameters(
        part_number="DIFFERENT",
        feedback_reference_voltage_v=0.8,
        switching_frequency_hz=500_000.0,
    )

    with pytest.raises(ValueError, match="does not match"):
        BuckSchematicBuilder().build(
            design_input,
            different_ic,
            result,
        )


def test_custom_pin_mapping_is_supported() -> None:
    design_input = _design_input()
    ic = _ic()
    result = BuckDesignEngine().design(design_input, ic)

    mapping = BuckSymbolMapping(
        vin_pin="8",
        gnd_pin="4",
        sw_pin="1",
        fb_pin="6",
        enable_pin=None,
        bootstrap_pin=None,
    )

    schematic = BuckSchematicBuilder().build(
        design_input,
        ic,
        result,
        symbol_mapping=mapping,
    )

    assert schematic.get_component("U1").get_pin_by_name(
        "VIN"
    ).number == "8"

    net_names = {net.name for net in schematic.nets}

    assert "EN" not in net_names
    assert "BOOT" not in net_names
    assert "CBOOT" not in {
        component.reference
        for component in schematic.components
    }


def test_serialized_model_contains_components_and_nets() -> None:
    schematic = _build()
    payload = schematic.to_dict()

    assert payload["name"].startswith("Buck_")
    assert len(payload["components"]) >= 8
    assert len(payload["nets"]) >= 5