from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
from uuid import UUID, uuid5

from src.schematic.model import (
    SchematicComponent,
    SchematicDesign,
    SchematicPin,
)


class KiCadSchematicExportError(Exception):
    """Raised when a modern KiCad schematic cannot be exported safely."""


@dataclass(frozen=True)
class SymbolPlacement:
    """Position and rotation of a symbol instance in millimetres."""

    x_mm: float
    y_mm: float
    rotation_deg: int = 0


@dataclass(frozen=True)
class PinGeometry:
    """
    Pin placement relative to the symbol origin.

    angle_deg follows KiCad's pin direction convention:
    0 points right, 90 up, 180 left, and 270 down.
    """

    x_mm: float
    y_mm: float
    angle_deg: int
    length_mm: float = 2.54


class KiCadSchematicExporter:
    """
    Export SchematicDesign directly to modern KiCad `.kicad_sch`.

    The exporter embeds custom symbol definitions inside the schematic, so the
    generated file does not depend on external KiCad symbol libraries.

    Connectivity is represented by labels placed exactly at symbol pin
    endpoints. In KiCad, labels sharing the same name are electrically
    connected. This avoids guessing graphical wire paths while retaining a
    valid editable netlist.
    """

    FILE_VERSION = 20231120
    GENERATOR = "llm_pcb"

    NAMESPACE = UUID("d61efc0a-568e-4fba-9799-d503b18b6742")

    DEFAULT_PLACEMENTS: Mapping[str, SymbolPlacement] = {
        "J1": SymbolPlacement(30.0, 75.0),
        "CIN": SymbolPlacement(55.0, 82.0),
        "U1": SymbolPlacement(90.0, 75.0),
        "CBOOT": SymbolPlacement(105.0, 52.0),
        "L1": SymbolPlacement(130.0, 70.0),
        "COUT": SymbolPlacement(155.0, 82.0),
        "R1": SymbolPlacement(180.0, 70.0),
        "R2": SymbolPlacement(180.0, 95.0),
        "J2": SymbolPlacement(215.0, 75.0),
    }

    def export(
        self,
        design: SchematicDesign,
        output_path: str | Path,
        placements: Optional[Mapping[str, SymbolPlacement]] = None,
    ) -> Path:
        design.validate()

        path = Path(output_path)
        if path.suffix.lower() != ".kicad_sch":
            raise KiCadSchematicExportError(
                "Modern KiCad schematic output must use "
                "the .kicad_sch extension."
            )

        placement_map = dict(self.DEFAULT_PLACEMENTS)
        if placements:
            placement_map.update(placements)

        missing = [
            component.reference
            for component in design.components
            if component.reference not in placement_map
        ]
        if missing:
            raise KiCadSchematicExportError(
                "Missing schematic placement for: "
                + ", ".join(sorted(missing))
            )

        self._validate_supported_rotations(placement_map)

        path.parent.mkdir(parents=True, exist_ok=True)

        project_name = self._safe_project_name(design.name)
        root_uuid = self._uuid(f"{project_name}:root")

        component_symbols = {
            component.reference: self._symbol_id(component)
            for component in design.components
        }

        pin_geometries = {
            component.reference: self._pin_geometries(component)
            for component in design.components
        }

        lines: List[str] = [
            "(kicad_sch",
            f"  (version {self.FILE_VERSION})",
            f"  (generator {self.GENERATOR})",
            f'  (uuid {root_uuid})',
            '  (paper "A4")',
            "  (lib_symbols",
        ]

        for component in design.components:
            lines.extend(
                self._library_symbol_block(
                    component=component,
                    symbol_id=component_symbols[component.reference],
                    indent="    ",
                )
            )

        lines.append("  )")

        for component in design.components:
            lines.extend(
                self._symbol_instance_block(
                    component=component,
                    symbol_id=component_symbols[component.reference],
                    placement=placement_map[component.reference],
                    root_uuid=root_uuid,
                    project_name=project_name,
                    indent="  ",
                )
            )

        lines.extend(
            self._net_wiring_blocks(
                design=design,
                placements=placement_map,
                pin_geometries=pin_geometries,
                project_name=project_name,
                indent="  ",
            )
        )

        lines.extend(
            [
                "  (sheet_instances",
                '    (path "/"',
                '      (page "1")',
                "    )",
                "  )",
                ")",
            ]
        )

        path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        return path

    def _library_symbol_block(
        self,
        component: SchematicComponent,
        symbol_id: str,
        indent: str,
    ) -> List[str]:
        geometries = self._pin_geometries(component)
        body_width, body_height = self._body_size(component)

        reference_prefix = self._reference_prefix(
            component.reference
        )

        lines = [
            f'{indent}(symbol "{self._escape(symbol_id)}"',
            f"{indent}  (pin_names (offset 1.016))",
            f"{indent}  (exclude_from_sim no)",
            f"{indent}  (in_bom yes)",
            f"{indent}  (on_board yes)",
            self._property(
                "Reference",
                reference_prefix,
                0,
                -(body_height / 2 + 2.54),
                indent + "  ",
            ),
            self._property(
                "Value",
                component.value,
                0,
                body_height / 2 + 2.54,
                indent + "  ",
            ),
            self._property(
                "Footprint",
                component.footprint_name or "",
                0,
                0,
                indent + "  ",
                hidden=True,
            ),
            self._property(
                "Datasheet",
                component.fields.get("datasheet_url", ""),
                0,
                0,
                indent + "  ",
                hidden=True,
            ),
            self._property(
                "Description",
                component.description or "",
                0,
                0,
                indent + "  ",
                hidden=True,
            ),
            f'{indent}  (symbol "{self._escape(symbol_id)}_0_1"',
            f"{indent}    (rectangle",
            f"{indent}      (start {-body_width / 2:.3f} "
            f"{-body_height / 2:.3f})",
            f"{indent}      (end {body_width / 2:.3f} "
            f"{body_height / 2:.3f})",
            f"{indent}      (stroke (width 0) "
            f"(type default))",
            f"{indent}      (fill (type background))",
            f"{indent}    )",
            f"{indent}  )",
            f'{indent}  (symbol "{self._escape(symbol_id)}_1_1"',
        ]

        for pin in component.pins:
            lines.extend(
                self._library_pin_block(
                    pin=pin,
                    geometry=geometries[pin.number],
                    indent=indent + "    ",
                )
            )

        lines.extend(
            [
                f"{indent}  )",
                f"{indent})",
            ]
        )
        return lines

    def _library_pin_block(
        self,
        pin: SchematicPin,
        geometry: PinGeometry,
        indent: str,
    ) -> List[str]:
        electrical_type = self._kicad_electrical_type(
            pin.electrical_type
        )

        return [
            f"{indent}(pin {electrical_type} line",
            f"{indent}  (at {geometry.x_mm:.3f} "
            f"{geometry.y_mm:.3f} {geometry.angle_deg})",
            f"{indent}  (length {geometry.length_mm:.3f})",
            f'{indent}  (name "{self._escape(pin.name)}"',
            f"{indent}    (effects (font (size 1.27 1.27)))",
            f"{indent}  )",
            f'{indent}  (number "{self._escape(pin.number)}"',
            f"{indent}    (effects (font (size 1.27 1.27)))",
            f"{indent}  )",
            f"{indent})",
        ]

    def _symbol_instance_block(
        self,
        component: SchematicComponent,
        symbol_id: str,
        placement: SymbolPlacement,
        root_uuid: str,
        project_name: str,
        indent: str,
    ) -> List[str]:
        symbol_uuid = self._uuid(
            f"{project_name}:symbol:{component.reference}"
        )
        body_width, body_height = self._body_size(component)

        lines = [
            f"{indent}(symbol",
            f'{indent}  (lib_id "{self._escape(symbol_id)}")',
            f"{indent}  (at {placement.x_mm:.3f} "
            f"{placement.y_mm:.3f} {placement.rotation_deg})",
            f"{indent}  (unit 1)",
            f"{indent}  (exclude_from_sim no)",
            f"{indent}  (in_bom yes)",
            f"{indent}  (on_board yes)",
            f"{indent}  (dnp no)",
            f"{indent}  (uuid {symbol_uuid})",
            self._instance_property(
                "Reference",
                component.reference,
                placement.x_mm,
                placement.y_mm - body_height / 2 - 3.0,
                indent + "  ",
            ),
            self._instance_property(
                "Value",
                component.value,
                placement.x_mm,
                placement.y_mm + body_height / 2 + 3.0,
                indent + "  ",
            ),
            self._instance_property(
                "Footprint",
                component.footprint_name or "",
                placement.x_mm,
                placement.y_mm,
                indent + "  ",
                hidden=True,
            ),
            self._instance_property(
                "Datasheet",
                component.fields.get("datasheet_url", ""),
                placement.x_mm,
                placement.y_mm,
                indent + "  ",
                hidden=True,
            ),
            self._instance_property(
                "Description",
                component.description or "",
                placement.x_mm,
                placement.y_mm,
                indent + "  ",
                hidden=True,
            ),
        ]

        for pin in component.pins:
            pin_uuid = self._uuid(
                f"{project_name}:symbol:{component.reference}:"
                f"pin:{pin.number}"
            )
            lines.append(
                f'{indent}  (pin "{self._escape(pin.number)}" '
                f"(uuid {pin_uuid}))"
            )

        lines.extend(
            [
                f"{indent}  (instances",
                f'{indent}    (project "{self._escape(project_name)}"',
                f'{indent}      (path "/{root_uuid}"',
                f'{indent}        (reference '
                f'"{self._escape(component.reference)}")',
                f"{indent}        (unit 1)",
                f"{indent}      )",
                f"{indent}    )",
                f"{indent}  )",
                f"{indent})",
            ]
        )
        return lines

    def _net_wiring_blocks(
        self,
        design: SchematicDesign,
        placements: Mapping[str, SymbolPlacement],
        pin_geometries: Mapping[str, Mapping[str, PinGeometry]],
        project_name: str,
        indent: str,
    ) -> List[str]:
        """
        Draw visible orthogonal wiring for every schematic net.

        Each net receives one horizontal trunk. Every connected pin is linked
        to that trunk with a vertical branch. Labels are placed on the trunk,
        and junctions are emitted where branches meet it.

        This representation is intentionally simple but produces visible,
        editable, electrically connected KiCad wires.
        """
        lines: List[str] = []

        for net_index, net in enumerate(design.nets):
            endpoints: List[Tuple[str, str, float, float]] = []

            for connection in net.connections:
                reference = connection.component_reference
                placement = placements[reference]
                geometry = pin_geometries[reference][
                    connection.pin_number
                ]
                x_mm, y_mm = self._pin_endpoint(
                    placement,
                    geometry,
                )
                endpoints.append(
                    (
                        reference,
                        connection.pin_number,
                        x_mm,
                        y_mm,
                    )
                )

            if len(endpoints) < 2:
                continue

            trunk_y = self._choose_trunk_y(
                net.name,
                [point[3] for point in endpoints],
                net_index,
            )
            min_x = min(point[2] for point in endpoints)
            max_x = max(point[2] for point in endpoints)

            # Extend the trunk slightly so the label is easy to see.
            trunk_start_x = self._snap_to_grid(min_x - 3.81)
            trunk_end_x = self._snap_to_grid(max_x + 3.81)

            lines.extend(
                self._wire_block(
                    start=(trunk_start_x, trunk_y),
                    end=(trunk_end_x, trunk_y),
                    identifier=self._uuid(
                        f"{project_name}:wire:{net.name}:trunk"
                    ),
                    indent=indent,
                )
            )

            for reference, pin_number, x_mm, y_mm in endpoints:
                branch_x = self._snap_to_grid(x_mm)

                # A short horizontal lead handles pin endpoints that are not
                # exactly on the 1.27 mm schematic grid after calculations.
                if not self._same_point(
                    (x_mm, y_mm),
                    (branch_x, y_mm),
                ):
                    lines.extend(
                        self._wire_block(
                            start=(x_mm, y_mm),
                            end=(branch_x, y_mm),
                            identifier=self._uuid(
                                f"{project_name}:wire:{net.name}:"
                                f"{reference}:{pin_number}:lead"
                            ),
                            indent=indent,
                        )
                    )

                if not self._same_point(
                    (branch_x, y_mm),
                    (branch_x, trunk_y),
                ):
                    lines.extend(
                        self._wire_block(
                            start=(branch_x, y_mm),
                            end=(branch_x, trunk_y),
                            identifier=self._uuid(
                                f"{project_name}:wire:{net.name}:"
                                f"{reference}:{pin_number}:branch"
                            ),
                            indent=indent,
                        )
                    )

                lines.extend(
                    self._junction_block(
                        x_mm=branch_x,
                        y_mm=trunk_y,
                        identifier=self._uuid(
                            f"{project_name}:junction:{net.name}:"
                            f"{reference}:{pin_number}"
                        ),
                        indent=indent,
                    )
                )

            lines.extend(
                self._label_block(
                    net_name=net.name,
                    x_mm=trunk_start_x,
                    y_mm=trunk_y,
                    identifier=self._uuid(
                        f"{project_name}:label:{net.name}"
                    ),
                    indent=indent,
                )
            )

        return lines

    def _wire_block(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        identifier: str,
        indent: str,
    ) -> List[str]:
        if self._same_point(start, end):
            return []

        return [
            f"{indent}(wire",
            f"{indent}  (pts",
            f"{indent}    (xy {start[0]:.3f} {start[1]:.3f})",
            f"{indent}    (xy {end[0]:.3f} {end[1]:.3f})",
            f"{indent}  )",
            f"{indent}  (stroke",
            f"{indent}    (width 0)",
            f"{indent}    (type default)",
            f"{indent}  )",
            f"{indent}  (uuid {identifier})",
            f"{indent})",
        ]

    @staticmethod
    def _junction_block(
        x_mm: float,
        y_mm: float,
        identifier: str,
        indent: str,
    ) -> List[str]:
        return [
            f"{indent}(junction",
            f"{indent}  (at {x_mm:.3f} {y_mm:.3f})",
            f"{indent}  (diameter 0)",
            f"{indent}  (color 0 0 0 0)",
            f"{indent}  (uuid {identifier})",
            f"{indent})",
        ]

    def _choose_trunk_y(
        self,
        net_name: str,
        endpoint_y_values: Sequence[float],
        net_index: int,
    ) -> float:
        """
        Choose separated trunk rows to keep the generated drawing readable.

        Named Buck nets receive stable preferred rows. Unknown nets are placed
        below the known rows using their index.
        """
        preferred = {
            "BOOT": 45.72,
            "VIN": 60.96,
            "SW": 68.58,
            "VOUT": 76.20,
            "FB": 88.90,
            "GND": 106.68,
        }

        if net_name.upper() in preferred:
            return preferred[net_name.upper()]

        average = sum(endpoint_y_values) / len(endpoint_y_values)
        candidate = average + net_index * 2.54
        return self._snap_to_grid(candidate)

    @staticmethod
    def _snap_to_grid(
        value: float,
        grid_mm: float = 1.27,
    ) -> float:
        return round(value / grid_mm) * grid_mm

    @staticmethod
    def _same_point(
        first: Tuple[float, float],
        second: Tuple[float, float],
        tolerance: float = 1e-6,
    ) -> bool:
        return (
            abs(first[0] - second[0]) <= tolerance
            and abs(first[1] - second[1]) <= tolerance
        )

    def _label_block(
        self,
        net_name: str,
        x_mm: float,
        y_mm: float,
        identifier: str,
        indent: str,
    ) -> List[str]:
        return [
            f'{indent}(label "{self._escape(net_name)}"',
            f"{indent}  (at {x_mm:.3f} {y_mm:.3f} 0)",
            f"{indent}  (effects",
            f"{indent}    (font (size 1.27 1.27))",
            f"{indent}    (justify left bottom)",
            f"{indent}  )",
            f"{indent}  (uuid {identifier})",
            f"{indent})",
        ]

    def _pin_geometries(
        self,
        component: SchematicComponent,
    ) -> Dict[str, PinGeometry]:
        if component.reference.startswith(("C", "R")):
            self._require_pin_count(component, 2)
            return {
                component.pins[0].number: PinGeometry(
                    0.0,
                    -3.81,
                    270,
                    2.54,
                ),
                component.pins[1].number: PinGeometry(
                    0.0,
                    3.81,
                    90,
                    2.54,
                ),
            }

        if component.reference.startswith("L"):
            self._require_pin_count(component, 2)
            return {
                component.pins[0].number: PinGeometry(
                    -5.08,
                    0.0,
                    0,
                    2.54,
                ),
                component.pins[1].number: PinGeometry(
                    5.08,
                    0.0,
                    180,
                    2.54,
                ),
            }

        if component.reference.startswith("J"):
            return self._connector_pin_geometries(component)

        if component.reference.startswith("U"):
            return self._ic_pin_geometries(component)

        raise KiCadSchematicExportError(
            f"Unsupported component reference: {component.reference}"
        )

    def _connector_pin_geometries(
        self,
        component: SchematicComponent,
    ) -> Dict[str, PinGeometry]:
        count = len(component.pins)
        if count < 1:
            raise KiCadSchematicExportError(
                f"{component.reference} has no pins."
            )

        start_y = -((count - 1) * 1.27)
        return {
            pin.number: PinGeometry(
                3.81,
                start_y + index * 2.54,
                180,
                2.54,
            )
            for index, pin in enumerate(component.pins)
        }

    def _ic_pin_geometries(
        self,
        component: SchematicComponent,
    ) -> Dict[str, PinGeometry]:
        named = {
            pin.name.strip().upper(): pin
            for pin in component.pins
        }

        geometries: Dict[str, PinGeometry] = {}

        left_order = ["VIN", "EN", "FB"]
        right_order = ["BOOT", "SW"]

        for index, name in enumerate(left_order):
            pin = named.get(name)
            if pin is not None:
                geometries[pin.number] = PinGeometry(
                    -7.62,
                    -2.54 + index * 2.54,
                    0,
                    2.54,
                )

        for index, name in enumerate(right_order):
            pin = named.get(name)
            if pin is not None:
                geometries[pin.number] = PinGeometry(
                    7.62,
                    -1.27 + index * 2.54,
                    180,
                    2.54,
                )

        ground_pin = named.get("GND")
        if ground_pin is not None:
            geometries[ground_pin.number] = PinGeometry(
                0.0,
                7.62,
                90,
                2.54,
            )

        unassigned = [
            pin
            for pin in component.pins
            if pin.number not in geometries
        ]

        for index, pin in enumerate(unassigned):
            geometries[pin.number] = PinGeometry(
                -7.62,
                5.08 + index * 2.54,
                0,
                2.54,
            )

        return geometries

    @staticmethod
    def _pin_endpoint(
        placement: SymbolPlacement,
        geometry: PinGeometry,
    ) -> Tuple[float, float]:
        if placement.rotation_deg != 0:
            raise KiCadSchematicExportError(
                "Pin endpoint calculation currently supports "
                "only zero-degree symbol rotation."
            )

        angle = geometry.angle_deg % 360

        dx = 0.0
        dy = 0.0

        if angle == 0:
            dx = geometry.length_mm
        elif angle == 90:
            dy = -geometry.length_mm
        elif angle == 180:
            dx = -geometry.length_mm
        elif angle == 270:
            dy = geometry.length_mm
        else:
            raise KiCadSchematicExportError(
                f"Unsupported pin angle: {geometry.angle_deg}"
            )

        return (
            placement.x_mm + geometry.x_mm + dx,
            placement.y_mm + geometry.y_mm + dy,
        )

    @staticmethod
    def _body_size(
        component: SchematicComponent,
    ) -> Tuple[float, float]:
        if component.reference.startswith("U"):
            return 10.16, 10.16
        if component.reference.startswith("J"):
            height = max(5.08, len(component.pins) * 2.54)
            return 5.08, height
        if component.reference.startswith("L"):
            return 5.08, 3.81
        return 3.81, 3.81

    @staticmethod
    def _require_pin_count(
        component: SchematicComponent,
        expected: int,
    ) -> None:
        if len(component.pins) != expected:
            raise KiCadSchematicExportError(
                f"{component.reference} must have exactly "
                f"{expected} pins."
            )

    @staticmethod
    def _connection_net_map(
        design: SchematicDesign,
    ) -> Dict[Tuple[str, str], str]:
        result: Dict[Tuple[str, str], str] = {}

        for net in design.nets:
            for connection in net.connections:
                result[
                    (
                        connection.component_reference,
                        connection.pin_number,
                    )
                ] = net.name

        return result

    @staticmethod
    def _kicad_electrical_type(
        electrical_type: str,
    ) -> str:
        mapping = {
            "passive": "passive",
            "input": "input",
            "output": "output",
            "bidirectional": "bidirectional",
            "tri_state": "tri_state",
            "power_in": "power_in",
            "power_out": "power_out",
            "open_collector": "open_collector",
            "open_emitter": "open_emitter",
            "no_connect": "no_connect",
            "unspecified": "unspecified",
        }
        return mapping.get(
            electrical_type.strip().lower(),
            "passive",
        )

    @staticmethod
    def _reference_prefix(reference: str) -> str:
        prefix = ""
        for character in reference:
            if character.isalpha():
                prefix += character
            else:
                break
        return prefix or "U"

    @staticmethod
    def _symbol_id(
        component: SchematicComponent,
    ) -> str:
        safe_reference = "".join(
            character
            if character.isalnum() or character == "_"
            else "_"
            for character in component.reference
        )
        return f"LLMPCB_{safe_reference}_SYMBOL"

    @staticmethod
    def _safe_project_name(name: str) -> str:
        safe = "".join(
            character
            if character.isalnum() or character in "_-"
            else "_"
            for character in name
        )
        return safe or "LLM_PCB_Design"

    def _uuid(self, key: str) -> str:
        return str(uuid5(self.NAMESPACE, key))

    @staticmethod
    def _property(
        name: str,
        value: str,
        x_mm: float,
        y_mm: float,
        indent: str,
        hidden: bool = False,
    ) -> str:
        hidden_token = " hide" if hidden else ""
        escaped_name = KiCadSchematicExporter._escape(name)
        escaped_value = KiCadSchematicExporter._escape(value)

        return (
            f'{indent}(property "{escaped_name}" "{escaped_value}" '
            f"(at {x_mm:.3f} {y_mm:.3f} 0)"
            f" (effects (font (size 1.27 1.27)){hidden_token}))"
        )

    @staticmethod
    def _instance_property(
        name: str,
        value: str,
        x_mm: float,
        y_mm: float,
        indent: str,
        hidden: bool = False,
    ) -> str:
        return KiCadSchematicExporter._property(
            name,
            value,
            x_mm,
            y_mm,
            indent,
            hidden,
        )

    @staticmethod
    def _validate_supported_rotations(
        placements: Mapping[str, SymbolPlacement],
    ) -> None:
        unsupported = [
            reference
            for reference, placement in placements.items()
            if placement.rotation_deg != 0
        ]
        if unsupported:
            raise KiCadSchematicExportError(
                "Modern schematic exporter currently supports "
                "only zero-degree rotation. Unsupported: "
                + ", ".join(sorted(unsupported))
            )

    @staticmethod
    def _escape(value: str) -> str:
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
