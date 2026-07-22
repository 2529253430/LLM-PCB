from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.design.buck_engine import (
    BuckDesignInput,
    BuckDesignResult,
    BuckICParameters,
)

from .model import (
    PinReference,
    SchematicComponent,
    SchematicDesign,
    SchematicNet,
    SchematicPin,
)


@dataclass(frozen=True)
class BuckSymbolMapping:
    """
    Logical pin mapping for the selected Buck regulator symbol.

    Real devices may use different physical pin numbers. The mapping should
    ultimately be populated from a verified symbol library or datasheet.
    """

    vin_pin: str = "1"
    gnd_pin: str = "2"
    sw_pin: str = "3"
    fb_pin: str = "4"
    enable_pin: Optional[str] = "5"
    bootstrap_pin: Optional[str] = "6"


class BuckSchematicBuilder:
    """Build a technology-neutral Buck schematic from engine results."""

    def build(
        self,
        design_input: BuckDesignInput,
        ic: BuckICParameters,
        result: BuckDesignResult,
        symbol_mapping: Optional[BuckSymbolMapping] = None,
        footprint_name: Optional[str] = None,
        manufacturer: Optional[str] = None,
    ) -> SchematicDesign:
        design_input.validate()
        ic.validate()

        if result.part_number != ic.part_number:
            raise ValueError(
                "BuckDesignResult part number does not match "
                "BuckICParameters part number."
            )

        mapping = symbol_mapping or BuckSymbolMapping()

        design = SchematicDesign(
            name=(
                f"Buck_{design_input.input_voltage_max_v:g}V_to_"
                f"{design_input.output_voltage_v:g}V_"
                f"{design_input.output_current_a:g}A"
            ),
            metadata={
                "topology": "buck",
                "selected_ic": ic.part_number,
                "input_voltage_min_v": (
                    f"{design_input.input_voltage_min_v:g}"
                ),
                "input_voltage_max_v": (
                    f"{design_input.input_voltage_max_v:g}"
                ),
                "output_voltage_v": (
                    f"{design_input.output_voltage_v:g}"
                ),
                "output_current_a": (
                    f"{design_input.output_current_a:g}"
                ),
                "enable_configuration": (
                    "tied_to_vin"
                    if mapping.enable_pin is not None
                    else "not_present"
                ),
            },
        )

        self._add_power_connectors(design, design_input)
        self._add_regulator(
            design,
            ic,
            mapping,
            footprint_name,
            manufacturer,
        )
        self._add_passive_components(design, result)
        self._add_optional_bootstrap_capacitor(design, mapping)
        self._add_nets(design, mapping)

        design.validate()
        return design

    @staticmethod
    def _add_power_connectors(
        design: SchematicDesign,
        design_input: BuckDesignInput,
    ) -> None:
        connector_pins = (
            SchematicPin("1", "PWR", "power_in"),
            SchematicPin("2", "GND", "power_in"),
        )

        design.add_component(
            SchematicComponent(
                reference="J1",
                value="VIN_INPUT",
                symbol_name="Connector_Generic:Conn_01x02",
                footprint_name="Connector_PinHeader_1x02",
                description=(
                    f"Input connector for "
                    f"{design_input.input_voltage_min_v:g}-"
                    f"{design_input.input_voltage_max_v:g} V"
                ),
                pins=connector_pins,
            )
        )

        design.add_component(
            SchematicComponent(
                reference="J2",
                value="VOUT_OUTPUT",
                symbol_name="Connector_Generic:Conn_01x02",
                footprint_name="Connector_PinHeader_1x02",
                description=(
                    f"Output connector for "
                    f"{design_input.output_voltage_v:g} V, "
                    f"{design_input.output_current_a:g} A"
                ),
                pins=connector_pins,
            )
        )

    @staticmethod
    def _add_regulator(
        design: SchematicDesign,
        ic: BuckICParameters,
        mapping: BuckSymbolMapping,
        footprint_name: Optional[str],
        manufacturer: Optional[str],
    ) -> None:
        pins = [
            SchematicPin(mapping.vin_pin, "VIN", "power_in"),
            SchematicPin(mapping.gnd_pin, "GND", "power_in"),
            SchematicPin(mapping.sw_pin, "SW", "power_out"),
            SchematicPin(mapping.fb_pin, "FB", "input"),
        ]

        if mapping.enable_pin is not None:
            pins.append(
                SchematicPin(
                    mapping.enable_pin,
                    "EN",
                    "input",
                )
            )

        if mapping.bootstrap_pin is not None:
            pins.append(
                SchematicPin(
                    mapping.bootstrap_pin,
                    "BOOT",
                    "passive",
                )
            )

        design.add_component(
            SchematicComponent(
                reference="U1",
                value=ic.part_number,
                symbol_name=f"Regulator_Switching:{ic.part_number}",
                footprint_name=footprint_name,
                manufacturer=manufacturer,
                part_number=ic.part_number,
                description="Selected Buck switching regulator",
                pins=tuple(pins),
                fields={
                    "feedback_reference_voltage_v": (
                        f"{ic.feedback_reference_voltage_v:g}"
                    ),
                    "switching_frequency_hz": (
                        f"{ic.switching_frequency_hz:g}"
                    ),
                    "synchronous_rectification": str(
                        ic.synchronous_rectification
                    ),
                },
            )
        )

    @staticmethod
    def _add_passive_components(
        design: SchematicDesign,
        result: BuckDesignResult,
    ) -> None:
        design.add_component(
            SchematicComponent(
                reference="CIN",
                value=(
                    f"{result.recommended_input_capacitance_f * 1e6:g}uF"
                ),
                symbol_name="Device:C",
                footprint_name="Capacitor_SMD:C_1210",
                description="Buck input bypass capacitor",
                pins=(
                    SchematicPin("1", "POS", "passive"),
                    SchematicPin("2", "NEG", "passive"),
                ),
                fields={
                    "voltage_rating_v": (
                        f"{result.recommended_input_capacitor_voltage_rating_v:g}"
                    ),
                    "rms_current_a": (
                        f"{result.input_capacitor_rms_current_a:g}"
                    ),
                },
            )
        )

        design.add_component(
            SchematicComponent(
                reference="L1",
                value=(
                    f"{result.recommended_inductance_h * 1e6:g}uH"
                ),
                symbol_name="Device:L",
                footprint_name="Inductor_SMD:L_Power",
                description="Buck output inductor",
                pins=(
                    SchematicPin("1", "IN", "passive"),
                    SchematicPin("2", "OUT", "passive"),
                ),
                fields={
                    "current_rating_a": (
                        f"{result.recommended_inductor_current_rating_a:g}"
                    ),
                    "peak_current_a": (
                        f"{result.inductor_peak_current_a:g}"
                    ),
                },
            )
        )

        design.add_component(
            SchematicComponent(
                reference="COUT",
                value=(
                    f"{result.recommended_output_capacitance_f * 1e6:g}uF"
                ),
                symbol_name="Device:C",
                footprint_name="Capacitor_SMD:C_1210",
                description="Buck output capacitor",
                pins=(
                    SchematicPin("1", "POS", "passive"),
                    SchematicPin("2", "NEG", "passive"),
                ),
                fields={
                    "voltage_rating_v": (
                        f"{result.recommended_output_capacitor_voltage_rating_v:g}"
                    ),
                    "maximum_esr_ohm": (
                        f"{result.maximum_output_capacitor_esr_ohm:g}"
                    ),
                },
            )
        )

        design.add_component(
            SchematicComponent(
                reference="R1",
                value=f"{result.feedback_top_resistance_ohm:g}",
                symbol_name="Device:R",
                footprint_name="Resistor_SMD:R_0603",
                description="Feedback upper resistor",
                pins=(
                    SchematicPin("1", "TOP", "passive"),
                    SchematicPin("2", "BOTTOM", "passive"),
                ),
            )
        )

        design.add_component(
            SchematicComponent(
                reference="R2",
                value=f"{result.feedback_bottom_resistance_ohm:g}",
                symbol_name="Device:R",
                footprint_name="Resistor_SMD:R_0603",
                description="Feedback lower resistor",
                pins=(
                    SchematicPin("1", "TOP", "passive"),
                    SchematicPin("2", "BOTTOM", "passive"),
                ),
            )
        )

    @staticmethod
    def _add_optional_bootstrap_capacitor(
        design: SchematicDesign,
        mapping: BuckSymbolMapping,
    ) -> None:
        if mapping.bootstrap_pin is None:
            return

        design.add_component(
            SchematicComponent(
                reference="CBOOT",
                value="100nF",
                symbol_name="Device:C",
                footprint_name="Capacitor_SMD:C_0603",
                description="Bootstrap capacitor",
                pins=(
                    SchematicPin("1", "BOOT", "passive"),
                    SchematicPin("2", "SW", "passive"),
                ),
            )
        )

    @staticmethod
    def _add_nets(
        design: SchematicDesign,
        mapping: BuckSymbolMapping,
    ) -> None:
        vin_connections = [
            PinReference("J1", "1"),
            PinReference("CIN", "1"),
            PinReference("U1", mapping.vin_pin),
        ]

        # An enable pin tied high belongs to the same VIN electrical net.
        # Creating a separate EN net would incorrectly place J1.1 on two nets.
        if mapping.enable_pin is not None:
            vin_connections.append(
                PinReference("U1", mapping.enable_pin)
            )

        design.add_net(
            SchematicNet(
                name="VIN",
                net_class="POWER",
                description=(
                    "Input supply rail; regulator enable is tied to VIN"
                    if mapping.enable_pin is not None
                    else "Input supply rail"
                ),
                connections=tuple(vin_connections),
            )
        )

        sw_connections = [
            PinReference("U1", mapping.sw_pin),
            PinReference("L1", "1"),
        ]

        if mapping.bootstrap_pin is not None:
            sw_connections.append(
                PinReference("CBOOT", "2")
            )

        design.add_net(
            SchematicNet(
                name="SW",
                net_class="SWITCHING",
                description="High dv/dt switching node",
                connections=tuple(sw_connections),
            )
        )

        design.add_net(
            SchematicNet(
                name="VOUT",
                net_class="POWER",
                description="Regulated output rail",
                connections=(
                    PinReference("L1", "2"),
                    PinReference("COUT", "1"),
                    PinReference("R1", "1"),
                    PinReference("J2", "1"),
                ),
            )
        )

        design.add_net(
            SchematicNet(
                name="FB",
                net_class="SIGNAL",
                description="Feedback sense node",
                connections=(
                    PinReference("R1", "2"),
                    PinReference("R2", "1"),
                    PinReference("U1", mapping.fb_pin),
                ),
            )
        )

        design.add_net(
            SchematicNet(
                name="GND",
                net_class="GROUND",
                description="Common power return",
                connections=(
                    PinReference("J1", "2"),
                    PinReference("J2", "2"),
                    PinReference("CIN", "2"),
                    PinReference("COUT", "2"),
                    PinReference("R2", "2"),
                    PinReference("U1", mapping.gnd_pin),
                ),
            )
        )

        if mapping.bootstrap_pin is not None:
            design.add_net(
                SchematicNet(
                    name="BOOT",
                    net_class="SIGNAL",
                    description="Bootstrap supply node",
                    connections=(
                        PinReference("U1", mapping.bootstrap_pin),
                        PinReference("CBOOT", "1"),
                    ),
                )
            )