from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Mapping, Tuple
from uuid import UUID, uuid5

from src.schematic.layout import (
    Junction,
    NetLabelLayout,
    PinLayout,
    Point,
    SchematicLayout,
    SymbolLayout,
    WireSegment,
)
from src.schematic.model import (
    SchematicComponent,
    SchematicDesign,
    SchematicPin,
)


class KiCadSchematicExportError(Exception):
    """Raised when a modern KiCad schematic cannot be exported safely."""


class KiCadSchematicExporter:
    """
    Export a logical SchematicDesign plus graphical SchematicLayout to a
    modern `.kicad_sch` file.

    Responsibilities:
    - serialize embedded symbol definitions;
    - serialize symbol instances;
    - serialize visible wires, junctions, and labels;
    - preserve deterministic UUIDs.

    Non-responsibilities:
    - choosing component positions;
    - calculating pin endpoints;
    - routing schematic wires;
    - deciding where labels or junctions should be placed.

    Those decisions belong to SchematicLayout.
    """

    FILE_VERSION = 20231120
    GENERATOR = "llm_pcb"
    NAMESPACE = UUID("d61efc0a-568e-4fba-9799-d503b18b6742")

    def export(
        self,
        design: SchematicDesign,
        layout: SchematicLayout,
        output_path: str | Path,
    ) -> Path:
        design.validate()
        layout.validate(design)

        path = Path(output_path)

        if path.suffix.lower() != ".kicad_sch":
            raise KiCadSchematicExportError(
                "Modern KiCad schematic output must use "
                "the .kicad_sch extension."
            )

        path.parent.mkdir(parents=True, exist_ok=True)

        project_name = self._safe_project_name(design.name)
        root_uuid = self._uuid(f"{project_name}:root")

        component_map = {
            component.reference: component
            for component in design.components
        }

        symbol_ids = {
            reference: self._symbol_id(reference)
            for reference in component_map
        }

        lines: List[str] = [
            "(kicad_sch",
            f"  (version {self.FILE_VERSION})",
            f"  (generator {self.GENERATOR})",
            f"  (uuid {root_uuid})",
            '  (paper "A4")',
            "  (lib_symbols",
        ]

        for component in design.components:
            symbol_layout = layout.get_symbol(
                component.reference
            )

            lines.extend(
                self._library_symbol_block(
                    component=component,
                    symbol_layout=symbol_layout,
                    pin_layouts=self._component_pin_layouts(
                        component,
                        layout,
                    ),
                    symbol_id=symbol_ids[
                        component.reference
                    ],
                    indent="    ",
                )
            )

        lines.append("  )")

        for component in design.components:
            lines.extend(
                self._symbol_instance_block(
                    component=component,
                    symbol_layout=layout.get_symbol(
                        component.reference
                    ),
                    symbol_id=symbol_ids[
                        component.reference
                    ],
                    project_name=project_name,
                    root_uuid=root_uuid,
                    indent="  ",
                )
            )

        for wire_index, wire in enumerate(layout.wires):
            lines.extend(
                self._wire_block(
                    wire=wire,
                    identifier=self._uuid(
                        f"{project_name}:wire:"
                        f"{wire_index}:{wire.net_name}:"
                        f"{wire.start.x}:{wire.start.y}:"
                        f"{wire.end.x}:{wire.end.y}"
                    ),
                    indent="  ",
                )
            )

        for junction_index, junction in enumerate(
            layout.junctions
        ):
            lines.extend(
                self._junction_block(
                    junction=junction,
                    identifier=self._uuid(
                        f"{project_name}:junction:"
                        f"{junction_index}:"
                        f"{junction.net_name}:"
                        f"{junction.position.x}:"
                        f"{junction.position.y}"
                    ),
                    indent="  ",
                )
            )

        for label_index, label in enumerate(layout.labels):
            lines.extend(
                self._label_block(
                    label=label,
                    identifier=self._uuid(
                        f"{project_name}:label:"
                        f"{label_index}:"
                        f"{label.net_name}:"
                        f"{label.position.x}:"
                        f"{label.position.y}"
                    ),
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
        symbol_layout: SymbolLayout,
        pin_layouts: Mapping[str, PinLayout],
        symbol_id: str,
        indent: str,
    ) -> List[str]:
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
                name="Reference",
                value=reference_prefix,
                x_mm=0.0,
                y_mm=(
                    -symbol_layout.body_height_mm / 2.0
                    - 2.54
                ),
                indent=indent + "  ",
            ),
            self._property(
                name="Value",
                value=component.value,
                x_mm=0.0,
                y_mm=(
                    symbol_layout.body_height_mm / 2.0
                    + 2.54
                ),
                indent=indent + "  ",
            ),
            self._property(
                name="Footprint",
                value=component.footprint_name or "",
                x_mm=0.0,
                y_mm=0.0,
                indent=indent + "  ",
                hidden=True,
            ),
            self._property(
                name="Datasheet",
                value=component.fields.get(
                    "datasheet_url",
                    "",
                ),
                x_mm=0.0,
                y_mm=0.0,
                indent=indent + "  ",
                hidden=True,
            ),
            self._property(
                name="Description",
                value=component.description or "",
                x_mm=0.0,
                y_mm=0.0,
                indent=indent + "  ",
                hidden=True,
            ),
            (
                f'{indent}  (symbol '
                f'"{self._escape(symbol_id)}_0_1"'
            ),
            f"{indent}    (rectangle",
            (
                f"{indent}      (start "
                f"{-symbol_layout.body_width_mm / 2.0:.3f} "
                f"{-symbol_layout.body_height_mm / 2.0:.3f})"
            ),
            (
                f"{indent}      (end "
                f"{symbol_layout.body_width_mm / 2.0:.3f} "
                f"{symbol_layout.body_height_mm / 2.0:.3f})"
            ),
            (
                f"{indent}      (stroke "
                f"(width 0) (type default))"
            ),
            f"{indent}      (fill (type background))",
            f"{indent}    )",
            f"{indent}  )",
            (
                f'{indent}  (symbol '
                f'"{self._escape(symbol_id)}_1_1"'
            ),
        ]

        for pin in component.pins:
            pin_layout = pin_layouts[pin.number]
            relative = Point(
                pin_layout.endpoint.x
                - symbol_layout.position.x,
                pin_layout.endpoint.y
                - symbol_layout.position.y,
            )

            geometry = self._pin_geometry_from_endpoint(
                relative=relative,
                symbol_layout=symbol_layout,
            )

            lines.extend(
                self._library_pin_block(
                    pin=pin,
                    x_mm=geometry[0],
                    y_mm=geometry[1],
                    angle_deg=geometry[2],
                    length_mm=geometry[3],
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
        x_mm: float,
        y_mm: float,
        angle_deg: int,
        length_mm: float,
        indent: str,
    ) -> List[str]:
        electrical_type = self._kicad_electrical_type(
            pin.electrical_type
        )

        return [
            f"{indent}(pin {electrical_type} line",
            (
                f"{indent}  (at "
                f"{x_mm:.3f} {y_mm:.3f} {angle_deg})"
            ),
            f"{indent}  (length {length_mm:.3f})",
            (
                f'{indent}  (name '
                f'"{self._escape(pin.name)}"'
            ),
            (
                f"{indent}    "
                f"(effects (font (size 1.27 1.27)))"
            ),
            f"{indent}  )",
            (
                f'{indent}  (number '
                f'"{self._escape(pin.number)}"'
            ),
            (
                f"{indent}    "
                f"(effects (font (size 1.27 1.27)))"
            ),
            f"{indent}  )",
            f"{indent})",
        ]

    def _symbol_instance_block(
        self,
        component: SchematicComponent,
        symbol_layout: SymbolLayout,
        symbol_id: str,
        project_name: str,
        root_uuid: str,
        indent: str,
    ) -> List[str]:
        symbol_uuid = self._uuid(
            f"{project_name}:symbol:{component.reference}"
        )

        lines = [
            f"{indent}(symbol",
            f'{indent}  (lib_id "{self._escape(symbol_id)}")',
            (
                f"{indent}  (at "
                f"{symbol_layout.position.x:.3f} "
                f"{symbol_layout.position.y:.3f} "
                f"{symbol_layout.rotation_deg})"
            ),
            f"{indent}  (unit 1)",
            f"{indent}  (exclude_from_sim no)",
            f"{indent}  (in_bom yes)",
            f"{indent}  (on_board yes)",
            f"{indent}  (dnp no)",
            f"{indent}  (uuid {symbol_uuid})",
            self._property(
                name="Reference",
                value=component.reference,
                x_mm=symbol_layout.position.x,
                y_mm=(
                    symbol_layout.position.y
                    - symbol_layout.body_height_mm / 2.0
                    - 3.0
                ),
                indent=indent + "  ",
            ),
            self._property(
                name="Value",
                value=component.value,
                x_mm=symbol_layout.position.x,
                y_mm=(
                    symbol_layout.position.y
                    + symbol_layout.body_height_mm / 2.0
                    + 3.0
                ),
                indent=indent + "  ",
            ),
            self._property(
                name="Footprint",
                value=component.footprint_name or "",
                x_mm=symbol_layout.position.x,
                y_mm=symbol_layout.position.y,
                indent=indent + "  ",
                hidden=True,
            ),
            self._property(
                name="Datasheet",
                value=component.fields.get(
                    "datasheet_url",
                    "",
                ),
                x_mm=symbol_layout.position.x,
                y_mm=symbol_layout.position.y,
                indent=indent + "  ",
                hidden=True,
            ),
            self._property(
                name="Description",
                value=component.description or "",
                x_mm=symbol_layout.position.x,
                y_mm=symbol_layout.position.y,
                indent=indent + "  ",
                hidden=True,
            ),
        ]

        for pin in component.pins:
            pin_uuid = self._uuid(
                f"{project_name}:symbol:"
                f"{component.reference}:pin:{pin.number}"
            )
            lines.append(
                f'{indent}  (pin '
                f'"{self._escape(pin.number)}" '
                f"(uuid {pin_uuid}))"
            )

        lines.extend(
            [
                f"{indent}  (instances",
                (
                    f'{indent}    (project '
                    f'"{self._escape(project_name)}"'
                ),
                f'{indent}      (path "/{root_uuid}"',
                (
                    f'{indent}        (reference '
                    f'"{self._escape(component.reference)}")'
                ),
                f"{indent}        (unit 1)",
                f"{indent}      )",
                f"{indent}    )",
                f"{indent}  )",
                f"{indent})",
            ]
        )

        return lines

    @staticmethod
    def _wire_block(
        wire: WireSegment,
        identifier: str,
        indent: str,
    ) -> List[str]:
        wire.validate()

        return [
            f"{indent}(wire",
            f"{indent}  (pts",
            (
                f"{indent}    (xy "
                f"{wire.start.x:.3f} {wire.start.y:.3f})"
            ),
            (
                f"{indent}    (xy "
                f"{wire.end.x:.3f} {wire.end.y:.3f})"
            ),
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
        junction: Junction,
        identifier: str,
        indent: str,
    ) -> List[str]:
        return [
            f"{indent}(junction",
            (
                f"{indent}  (at "
                f"{junction.position.x:.3f} "
                f"{junction.position.y:.3f})"
            ),
            f"{indent}  (diameter 0)",
            f"{indent}  (color 0 0 0 0)",
            f"{indent}  (uuid {identifier})",
            f"{indent})",
        ]

    @staticmethod
    def _label_block(
        label: NetLabelLayout,
        identifier: str,
        indent: str,
    ) -> List[str]:
        return [
            (
                f'{indent}(label '
                f'"{KiCadSchematicExporter._escape(label.net_name)}"'
            ),
            (
                f"{indent}  (at "
                f"{label.position.x:.3f} "
                f"{label.position.y:.3f} "
                f"{label.rotation_deg})"
            ),
            f"{indent}  (effects",
            (
                f"{indent}    "
                f"(font (size 1.27 1.27))"
            ),
            f"{indent}    (justify left bottom)",
            f"{indent}  )",
            f"{indent}  (uuid {identifier})",
            f"{indent})",
        ]

    @staticmethod
    def _component_pin_layouts(
        component: SchematicComponent,
        layout: SchematicLayout,
    ) -> Dict[str, PinLayout]:
        return {
            pin.number: layout.get_pin(
                component.reference,
                pin.number,
            )
            for pin in component.pins
        }

    @staticmethod
    def _pin_geometry_from_endpoint(
        relative: Point,
        symbol_layout: SymbolLayout,
    ) -> Tuple[float, float, int, float]:
        """
        Convert an absolute endpoint relationship into a KiCad library pin.

        SchematicLayout stores the external endpoint. KiCad library pins store
        the pin root and length. The root is placed on the body boundary and
        the pin extends outward to the endpoint.
        """
        half_width = symbol_layout.body_width_mm / 2.0
        half_height = symbol_layout.body_height_mm / 2.0

        horizontal_overflow = abs(relative.x) - half_width
        vertical_overflow = abs(relative.y) - half_height

        if horizontal_overflow >= vertical_overflow:
            if relative.x < 0:
                root_x = -half_width
                length = abs(relative.x - root_x)
                return root_x, relative.y, 180, max(length, 1.27)

            root_x = half_width
            length = abs(relative.x - root_x)
            return root_x, relative.y, 0, max(length, 1.27)

        if relative.y < 0:
            root_y = -half_height
            length = abs(relative.y - root_y)
            return relative.x, root_y, 90, max(length, 1.27)

        root_y = half_height
        length = abs(relative.y - root_y)
        return relative.x, root_y, 270, max(length, 1.27)

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
    def _symbol_id(reference: str) -> str:
        safe_reference = "".join(
            character
            if character.isalnum() or character == "_"
            else "_"
            for character in reference
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

        return (
            f'{indent}(property '
            f'"{KiCadSchematicExporter._escape(name)}" '
            f'"{KiCadSchematicExporter._escape(value)}" '
            f"(at {x_mm:.3f} {y_mm:.3f} 0) "
            f"(effects (font (size 1.27 1.27))"
            f"{hidden_token}))"
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
