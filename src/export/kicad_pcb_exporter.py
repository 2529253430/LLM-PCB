from __future__ import annotations

import math
import uuid
from pathlib import Path

from src.eda.design import (
    EDAComponent,
    EDADesign,
    EDAPad,
)


class KiCadPCBExporter:
    """
    将 EDADesign 导出为 KiCad .kicad_pcb 文件。
    """

    FILE_VERSION = "20240108"
    GENERATOR = "llm-pcb"

    UUID_NAMESPACE = uuid.UUID(
        "7c1e6e0d-b16e-4c91-a2bb-57083f86cc31"
    )

    def export(
        self,
        design: EDADesign,
        output_path: str | Path,
    ) -> Path:
        """
        将 EDADesign 写入 .kicad_pcb 文件。
        """

        errors = design.validate()

        if errors:
            raise ValueError(
                "Cannot export an invalid EDA design: "
                + "; ".join(errors)
            )

        path = Path(output_path)

        if path.suffix.lower() != ".kicad_pcb":
            path = path.with_suffix(
                ".kicad_pcb"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            self.generate(design),
            encoding="utf-8",
            newline="\n",
        )

        return path

    def generate(
        self,
        design: EDADesign,
    ) -> str:
        """
        生成 KiCad PCB S-expression 文本。
        """

        net_numbers = (
            self._build_net_numbers(
                design
            )
        )

        pad_nets = (
            self._build_pad_net_map(
                design
            )
        )

        lines: list[str] = [
            (
                f'(kicad_pcb '
                f'(version {self.FILE_VERSION}) '
                f'(generator "{self.GENERATOR}")'
            ),
            "  (general",
            "    (thickness 1.6)",
            "  )",
            '  (paper "A4")',
            "  (layers",
            '    (0 "F.Cu" signal)',
            '    (31 "B.Cu" signal)',
            (
                '    (36 "B.SilkS" '
                'user "b.silkscreen")'
            ),
            (
                '    (37 "F.SilkS" '
                'user "f.silkscreen")'
            ),
            '    (44 "Edge.Cuts" user)',
            '    (48 "B.Fab" user)',
            '    (49 "F.Fab" user)',
            "  )",
            "  (setup",
            "    (pad_to_mask_clearance 0)",
            "  )",
            '  (net 0 "")',
        ]

        for net_name, net_number in (
            net_numbers.items()
        ):
            escaped_name = self._escape(
                net_name
            )

            lines.append(
                f'  (net {net_number} '
                f'"{escaped_name}")'
            )

        for component in (
            design.components.values()
        ):
            lines.extend(
                self._render_footprint(
                    component=component,
                    net_numbers=net_numbers,
                    pad_nets=pad_nets,
                )
            )

        lines.extend(
            self._render_board_outline(
                design
            )
        )

        for net_name, routed_net in (
            design.routed_nets.items()
        ):
            net_number = net_numbers[
                net_name
            ]

            for index, segment in enumerate(
                routed_net.segments
            ):
                layer = (
                    self._normalize_copper_layer(
                        segment.layer
                    )
                )

                segment_uuid = self._uuid(
                    f"segment:{net_name}:{index}"
                )

                lines.extend(
                    [
                        "  (segment",
                        (
                            "    (start "
                            f"{self._number(segment.start.x)} "
                            f"{self._number(segment.start.y)})"
                        ),
                        (
                            "    (end "
                            f"{self._number(segment.end.x)} "
                            f"{self._number(segment.end.y)})"
                        ),
                        (
                            "    (width "
                            f"{self._number(segment.width)})"
                        ),
                        f'    (layer "{layer}")',
                        f"    (net {net_number})",
                        (
                            "    (tstamp "
                            f"{segment_uuid})"
                        ),
                        "  )",
                    ]
                )

        lines.append(")")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _build_net_numbers(
        design: EDADesign,
    ) -> dict[str, int]:
        """
        为网络分配编号。
        """

        return {
            net_name: index
            for index, net_name in enumerate(
                design.nets.keys(),
                start=1,
            )
        }

    @staticmethod
    def _build_pad_net_map(
        design: EDADesign,
    ) -> dict[tuple[str, str], str]:
        """
        建立焊盘到网络的映射。
        """

        pad_nets: dict[
            tuple[str, str],
            str,
        ] = {}

        for net_name, net in (
            design.nets.items()
        ):
            for connection in (
                net.connections
            ):
                key = (
                    connection.reference,
                    connection.pad_number,
                )

                previous_net = (
                    pad_nets.get(key)
                )

                if (
                    previous_net is not None
                    and previous_net != net_name
                ):
                    raise ValueError(
                        "A pad cannot belong to "
                        "multiple nets: "
                        f"{key[0]}.{key[1]}"
                    )

                pad_nets[key] = net_name

        return pad_nets

    def _render_footprint(
        self,
        component: EDAComponent,
        net_numbers: dict[str, int],
        pad_nets: dict[
            tuple[str, str],
            str,
        ],
    ) -> list[str]:
        """
        输出一个 footprint。
        """

        footprint_name = (
            component.footprint_name
            or "Generic"
        )

        value = (
            component.part_number
            or component.value
            or component.component_type
        )

        (
            half_width,
            half_height,
        ) = (
            self._component_outline_half_size(
                component
            )
        )

        footprint_uuid = self._uuid(
            f"footprint:{component.reference}"
        )

        reference_y = self._number(
            -half_height - 1.5
        )

        value_y = self._number(
            half_height + 1.5
        )

        lines = [
            (
                '  (footprint "LLM-PCB:'
                f'{self._escape(footprint_name)}"'
            ),
            '    (layer "F.Cu")',
            (
                "    (at "
                f"{self._number(component.position.x)} "
                f"{self._number(component.position.y)} "
                f"{self._number(component.rotation)})"
            ),
            (
                "    (tstamp "
                f"{footprint_uuid})"
            ),
            (
                '    (property "Reference" '
                f'"{self._escape(component.reference)}"'
            ),
            (
                f"      (at 0 "
                f"{reference_y} 0)"
            ),
            '      (layer "F.SilkS")',
            (
                "      (effects "
                "(font "
                "(size 1 1) "
                "(thickness 0.15)))"
            ),
            "    )",
            (
                '    (property "Value" '
                f'"{self._escape(value)}"'
            ),
            (
                f"      (at 0 "
                f"{value_y} 0)"
            ),
            '      (layer "F.Fab")',
            (
                "      (effects "
                "(font "
                "(size 1 1) "
                "(thickness 0.15)))"
            ),
            "    )",
        ]

        lines.extend(
            self._render_footprint_outline(
                component=component,
                half_width=half_width,
                half_height=half_height,
            )
        )

        for pad in (
            component.pads.values()
        ):
            lines.append(
                self._render_pad(
                    component=component,
                    pad=pad,
                    net_numbers=net_numbers,
                    pad_nets=pad_nets,
                )
            )

        lines.append("  )")

        return lines

    def _render_footprint_outline(
        self,
        component: EDAComponent,
        half_width: float,
        half_height: float,
    ) -> list[str]:
        """
        输出简化丝印矩形。
        """

        edges = [
            (
                -half_width,
                -half_height,
                half_width,
                -half_height,
            ),
            (
                half_width,
                -half_height,
                half_width,
                half_height,
            ),
            (
                half_width,
                half_height,
                -half_width,
                half_height,
            ),
            (
                -half_width,
                half_height,
                -half_width,
                -half_height,
            ),
        ]

        lines: list[str] = []

        for index, (
            start_x,
            start_y,
            end_x,
            end_y,
        ) in enumerate(edges):
            edge_uuid = self._uuid(
                "outline:"
                f"{component.reference}:"
                f"{index}"
            )

            lines.extend(
                [
                    "    (fp_line",
                    (
                        "      (start "
                        f"{self._number(start_x)} "
                        f"{self._number(start_y)})"
                    ),
                    (
                        "      (end "
                        f"{self._number(end_x)} "
                        f"{self._number(end_y)})"
                    ),
                    (
                        "      (stroke "
                        "(width 0.15) "
                        "(type default))"
                    ),
                    '      (layer "F.SilkS")',
                    (
                        "      (tstamp "
                        f"{edge_uuid})"
                    ),
                    "    )",
                ]
            )

        return lines

    def _render_pad(
        self,
        component: EDAComponent,
        pad: EDAPad,
        net_numbers: dict[str, int],
        pad_nets: dict[
            tuple[str, str],
            str,
        ],
    ) -> str:
        """
        输出一个 SMD 焊盘。
        """

        local_x, local_y = (
            self._absolute_to_local(
                component=component,
                absolute_x=pad.position.x,
                absolute_y=pad.position.y,
            )
        )

        shape = self._normalize_pad_shape(
            pad.shape
        )

        net_name = pad_nets.get(
            (
                component.reference,
                pad.number,
            ),
            "",
        )

        net_clause = ""

        if net_name:
            escaped_net = self._escape(
                net_name
            )

            net_clause = (
                f' (net {net_numbers[net_name]} '
                f'"{escaped_net}")'
            )

        pad_uuid = self._uuid(
            "pad:"
            f"{component.reference}:"
            f"{pad.number}"
        )

        pad_number = self._escape(
            pad.number
        )

        return (
            f'    (pad "{pad_number}" '
            f"smd {shape} "
            f"(at {self._number(local_x)} "
            f"{self._number(local_y)}) "
            f"(size {self._number(pad.width)} "
            f"{self._number(pad.height)}) "
            f'(layers "F.Cu" "F.Paste" "F.Mask")'
            f"{net_clause} "
            f"(tstamp {pad_uuid}))"
        )

    def _render_board_outline(
        self,
        design: EDADesign,
    ) -> list[str]:
        """
        输出矩形板框。
        """

        edges = [
            (
                0.0,
                0.0,
                design.board_width,
                0.0,
            ),
            (
                design.board_width,
                0.0,
                design.board_width,
                design.board_height,
            ),
            (
                design.board_width,
                design.board_height,
                0.0,
                design.board_height,
            ),
            (
                0.0,
                design.board_height,
                0.0,
                0.0,
            ),
        ]

        lines: list[str] = []

        for index, (
            start_x,
            start_y,
            end_x,
            end_y,
        ) in enumerate(edges):
            edge_uuid = self._uuid(
                f"board-edge:{index}"
            )

            lines.extend(
                [
                    "  (gr_line",
                    (
                        "    (start "
                        f"{self._number(start_x)} "
                        f"{self._number(start_y)})"
                    ),
                    (
                        "    (end "
                        f"{self._number(end_x)} "
                        f"{self._number(end_y)})"
                    ),
                    (
                        "    (stroke "
                        "(width 0.05) "
                        "(type default))"
                    ),
                    '    (layer "Edge.Cuts")',
                    (
                        "    (tstamp "
                        f"{edge_uuid})"
                    ),
                    "  )",
                ]
            )

        return lines

    @staticmethod
    def _component_outline_half_size(
        component: EDAComponent,
    ) -> tuple[float, float]:
        """
        根据焊盘范围估算元件外框。
        """

        if not component.pads:
            return (
                2.5,
                2.5,
            )

        pad_entries: list[
            tuple[
                float,
                float,
                EDAPad,
            ]
        ] = []

        for pad in (
            component.pads.values()
        ):
            (
                local_x,
                local_y,
            ) = (
                KiCadPCBExporter
                ._absolute_to_local(
                    component=component,
                    absolute_x=pad.position.x,
                    absolute_y=pad.position.y,
                )
            )

            pad_entries.append(
                (
                    local_x,
                    local_y,
                    pad,
                )
            )

        maximum_x = max(
            abs(local_x)
            + pad.width / 2
            for (
                local_x,
                _,
                pad,
            ) in pad_entries
        )

        maximum_y = max(
            abs(local_y)
            + pad.height / 2
            for (
                _,
                local_y,
                pad,
            ) in pad_entries
        )

        return (
            max(
                1.5,
                maximum_x + 0.5,
            ),
            max(
                1.5,
                maximum_y + 0.5,
            ),
        )

    @staticmethod
    def _absolute_to_local(
        component: EDAComponent,
        absolute_x: float,
        absolute_y: float,
    ) -> tuple[float, float]:
        """
        将绝对焊盘坐标转换为封装局部坐标。
        """

        delta_x = (
            absolute_x
            - component.position.x
        )

        delta_y = (
            absolute_y
            - component.position.y
        )

        angle = math.radians(
            -component.rotation
        )

        cosine = math.cos(angle)
        sine = math.sin(angle)

        local_x = (
            delta_x * cosine
            - delta_y * sine
        )

        local_y = (
            delta_x * sine
            + delta_y * cosine
        )

        return (
            local_x,
            local_y,
        )

    @staticmethod
    def _normalize_pad_shape(
        shape: str,
    ) -> str:
        """
        转换焊盘形状名称。
        """

        mapping = {
            "rectangle": "rect",
            "rect": "rect",
            "circle": "circle",
            "oval": "oval",
            "roundrect": "roundrect",
        }

        return mapping.get(
            shape.strip().lower(),
            "rect",
        )

    @staticmethod
    def _normalize_copper_layer(
        layer: str,
    ) -> str:
        """
        转换内部铜层名称。
        """

        mapping = {
            "Top": "F.Cu",
            "Bottom": "B.Cu",
            "F.Cu": "F.Cu",
            "B.Cu": "B.Cu",
        }

        normalized = mapping.get(
            layer,
            layer,
        )

        if normalized not in {
            "F.Cu",
            "B.Cu",
        }:
            raise ValueError(
                "Unsupported routing layer: "
                f"{layer}"
            )

        return normalized

    @classmethod
    def _uuid(
        cls,
        key: str,
    ) -> str:
        """
        生成稳定 UUID。
        """

        return str(
            uuid.uuid5(
                cls.UUID_NAMESPACE,
                key,
            )
        )

    @staticmethod
    def _number(
        value: float,
    ) -> str:
        """
        格式化浮点数。
        """

        rounded = round(
            float(value),
            6,
        )

        if rounded == 0:
            rounded = 0.0

        text = (
            f"{rounded:.6f}"
            .rstrip("0")
            .rstrip(".")
        )

        return text or "0"

    @staticmethod
    def _escape(
        text: str,
    ) -> str:
        """
        转义 KiCad 字符串。
        """

        return (
            str(text)
            .replace(
                "\\",
                "\\\\",
            )
            .replace(
                '"',
                '\\"',
            )
            .replace(
                "\n",
                " ",
            )
            .replace(
                "\r",
                " ",
            )
        )