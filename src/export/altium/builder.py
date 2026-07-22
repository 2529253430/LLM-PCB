from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from src.design_ir import (
    SchematicDesignAdapter,
    UniversalProjectIR,
    UniversalProjectValidator,
)
from src.schematic.layout import SchematicLayout
from src.schematic.model import SchematicDesign

from .model import (
    AltiumComponent,
    AltiumConnection,
    AltiumNet,
    AltiumProjectModel,
    AltiumSymbolPlacement,
    AltiumWire,
)


class AltiumProjectBuildError(Exception):
    """Raised when an Altium intermediate project cannot be built."""


class AltiumProjectBuilder:
    """Map the universal project IR to the Altium intermediate model."""

    def build_from_ir(
        self,
        project_ir: UniversalProjectIR,
        *,
        project_name: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> AltiumProjectModel:
        """Build an Altium mapping model directly from universal IR."""

        try:
            UniversalProjectValidator().require_valid(project_ir)
        except ValueError as exc:
            raise AltiumProjectBuildError(
                f"Invalid UniversalProjectIR: {exc}"
            ) from exc

        resolved_project_name = (
            project_name or project_ir.project_name
        )
        if not resolved_project_name.strip():
            raise AltiumProjectBuildError(
                "project_name cannot be empty."
            )

        reference_by_component_id = {
            component.id: component.reference
            for component in project_ir.components
        }
        net_name_by_id = {
            net.id: net.name for net in project_ir.nets
        }

        components = [
            AltiumComponent(
                reference=component.reference,
                value=component.value,
                symbol_name=component.symbol_name,
                footprint_name=component.footprint_name,
                manufacturer=component.manufacturer,
                part_number=component.part_number,
                description=component.description,
                fields={
                    str(key): str(value)
                    for key, value in component.parameters.items()
                },
                pins=tuple(
                    (
                        pin.number,
                        pin.name,
                        pin.electrical_type,
                    )
                    for pin in component.pins
                ),
            )
            for component in project_ir.components
        ]

        nets = [
            AltiumNet(
                name=net.name,
                connections=tuple(
                    AltiumConnection(
                        component_reference=(
                            reference_by_component_id[
                                connection.component_id
                            ]
                        ),
                        pin_number=connection.pin_number,
                    )
                    for connection in net.connections
                ),
                net_class=net.net_class,
                description=net.description,
            )
            for net in project_ir.nets
        ]

        placements = [
            AltiumSymbolPlacement(
                reference=reference_by_component_id[
                    placement.component_id
                ],
                x_mm=placement.position.x_mm,
                y_mm=placement.position.y_mm,
                rotation_deg=placement.rotation_deg,
                body_width_mm=placement.body_size.width_mm,
                body_height_mm=placement.body_size.height_mm,
            )
            for placement
            in project_ir.schematic.symbol_placements
        ]

        wires = [
            AltiumWire(
                net_name=net_name_by_id[wire.net_id],
                start_x_mm=wire.segment.start.x_mm,
                start_y_mm=wire.segment.start.y_mm,
                end_x_mm=wire.segment.end.x_mm,
                end_y_mm=wire.segment.end.y_mm,
            )
            for wire in project_ir.schematic.wires
        ]

        combined: Dict[str, Any] = {
            "source": "LLM-PCB",
            "source_ir_schema": project_ir.SCHEMA_NAME,
            "source_ir_version": project_ir.schema_version,
            "source_project_id": project_ir.project_id,
            "source_design_name": project_ir.schematic.name,
            "target_eda": "altium",
            "mapping": "UniversalProjectIR->AltiumProjectModel",
        }
        combined.update(dict(project_ir.metadata))
        combined.update(dict(project_ir.schematic.metadata))
        combined.update(dict(metadata or {}))

        model = AltiumProjectModel(
            project_name=resolved_project_name,
            design_name=project_ir.schematic.name,
            grid_mm=project_ir.schematic.grid_mm,
            components=components,
            nets=nets,
            placements=placements,
            wires=wires,
            metadata=combined,
        )
        model.validate()
        return model

    def build(
        self,
        *,
        project_name: str,
        schematic: SchematicDesign,
        layout: SchematicLayout,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> AltiumProjectModel:
        """Compatibility wrapper for the pre-IR public API."""

        try:
            project_ir = SchematicDesignAdapter().build(
                schematic,
                layout,
                project_name=project_name,
                metadata=metadata,
            )
        except Exception as exc:
            raise AltiumProjectBuildError(
                f"Failed to create UniversalProjectIR: {exc}"
            ) from exc

        return self.build_from_ir(
            project_ir,
            project_name=project_name,
            metadata=metadata,
        )
