from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional

from src.schematic.layout import SchematicLayout
from src.schematic.model import SchematicDesign

from ..component import IRComponent, IRPin
from ..connectivity import IRNet, IRPinRef
from ..constraints import IRConstraintSet
from ..geometry import IRPoint, IRSegment, IRSize
from ..project import UniversalProjectIR
from ..schematic import (
    IRJunction,
    IRNetLabel,
    IRPinPlacement,
    IRSchematic,
    IRSymbolPlacement,
    IRWire,
)
from ..validator import UniversalProjectValidator


class SchematicDesignAdapterError(Exception):
    """Raised when a schematic cannot be converted to universal IR."""


class SchematicDesignAdapter:
    """Convert existing schematic models into UniversalProjectIR.

    The adapter is deliberately independent of KiCad. Its output is the
    canonical input for the Altium export pipeline.
    """

    def build(
        self,
        design: SchematicDesign,
        layout: SchematicLayout,
        *,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        constraints: Optional[IRConstraintSet] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        validate: bool = True,
    ) -> UniversalProjectIR:
        try:
            design.validate()
            layout.validate(design)
        except Exception as exc:
            raise SchematicDesignAdapterError(
                f"Source schematic validation failed: {exc}"
            ) from exc

        component_ids = {
            component.reference: self._component_id(component.reference)
            for component in design.components
        }
        net_ids = {
            net.name: self._net_id(net.name)
            for net in design.nets
        }

        components = tuple(
            IRComponent(
                id=component_ids[component.reference],
                reference=component.reference,
                value=component.value,
                symbol_name=component.symbol_name,
                footprint_name=component.footprint_name,
                manufacturer=component.manufacturer,
                part_number=component.part_number,
                description=component.description,
                parameters=dict(component.fields),
                metadata={
                    "source_model": "SchematicComponent",
                },
                pins=tuple(
                    IRPin(
                        number=pin.number,
                        name=pin.name,
                        electrical_type=pin.electrical_type,
                    )
                    for pin in component.pins
                ),
            )
            for component in design.components
        )

        nets = tuple(
            IRNet(
                id=net_ids[net.name],
                name=net.name,
                net_class=net.net_class,
                description=net.description,
                connections=tuple(
                    IRPinRef(
                        component_id=component_ids[
                            connection.component_reference
                        ],
                        pin_number=connection.pin_number,
                    )
                    for connection in net.connections
                ),
                metadata={
                    "source_model": "SchematicNet",
                },
            )
            for net in design.nets
        )

        symbol_placements = tuple(
            IRSymbolPlacement(
                component_id=component_ids[reference],
                position=IRPoint(
                    x_mm=symbol.position.x,
                    y_mm=symbol.position.y,
                ),
                body_size=IRSize(
                    width_mm=symbol.body_width_mm,
                    height_mm=symbol.body_height_mm,
                ),
                rotation_deg=symbol.rotation_deg,
                metadata={
                    "source_model": "SymbolLayout",
                },
            )
            for reference, symbol in sorted(
                layout.symbols.items(),
                key=lambda item: item[0],
            )
        )

        pin_placements = tuple(
            IRPinPlacement(
                component_id=component_ids[
                    pin.component_reference
                ],
                pin_number=pin.pin_number,
                endpoint=IRPoint(
                    x_mm=pin.endpoint.x,
                    y_mm=pin.endpoint.y,
                ),
            )
            for _, pin in sorted(
                layout.pins.items(),
                key=lambda item: item[0],
            )
        )

        wires = tuple(
            IRWire(
                net_id=net_ids[wire.net_name],
                segment=IRSegment(
                    start=IRPoint(
                        x_mm=wire.start.x,
                        y_mm=wire.start.y,
                    ),
                    end=IRPoint(
                        x_mm=wire.end.x,
                        y_mm=wire.end.y,
                    ),
                ),
                metadata={
                    "source_model": "WireSegment",
                },
            )
            for wire in layout.wires
        )

        junctions = tuple(
            IRJunction(
                net_id=net_ids[junction.net_name],
                position=IRPoint(
                    x_mm=junction.position.x,
                    y_mm=junction.position.y,
                ),
            )
            for junction in layout.junctions
        )

        labels = tuple(
            IRNetLabel(
                net_id=net_ids[label.net_name],
                position=IRPoint(
                    x_mm=label.position.x,
                    y_mm=label.position.y,
                ),
                text=label.net_name,
                rotation_deg=label.rotation_deg,
            )
            for label in layout.labels
        )

        merged_metadata: Dict[str, Any] = {}
        merged_metadata.update(design.metadata)
        merged_metadata.update(layout.metadata)
        if metadata:
            merged_metadata.update(metadata)
        merged_metadata.update(
            {
                "source_design_name": design.name,
                "target_eda": "altium",
                "adapter": (
                    "src.design_ir.adapters."
                    "SchematicDesignAdapter"
                ),
            }
        )

        resolved_name = project_name or design.name
        resolved_id = project_id or (
            f"project:{self._slug(resolved_name)}"
        )

        project = UniversalProjectIR(
            project_id=resolved_id,
            project_name=resolved_name,
            schematic=IRSchematic(
                name=layout.design_name or design.name,
                grid_mm=layout.grid_mm,
                symbol_placements=symbol_placements,
                pin_placements=pin_placements,
                wires=wires,
                junctions=junctions,
                labels=labels,
                metadata={
                    "source_model": "SchematicLayout",
                },
            ),
            components=components,
            nets=nets,
            constraints=constraints or IRConstraintSet(),
            metadata=merged_metadata,
        )

        if validate:
            try:
                UniversalProjectValidator().require_valid(project)
            except ValueError as exc:
                raise SchematicDesignAdapterError(
                    f"Generated UniversalProjectIR is invalid: {exc}"
                ) from exc

        return project

    @classmethod
    def _component_id(cls, reference: str) -> str:
        return f"component:{cls._slug(reference)}"

    @classmethod
    def _net_id(cls, name: str) -> str:
        return f"net:{cls._slug(name)}"

    @staticmethod
    def _slug(value: str) -> str:
        normalized = value.strip()
        normalized = re.sub(r"\s+", "_", normalized)
        normalized = re.sub(
            r"[^A-Za-z0-9_.:+-]",
            "_",
            normalized,
        )
        normalized = re.sub(r"_+", "_", normalized)
        return normalized or "unnamed"
