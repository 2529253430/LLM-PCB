from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

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
    def build(
        self,
        *,
        project_name: str,
        schematic: SchematicDesign,
        layout: SchematicLayout,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> AltiumProjectModel:
        if not project_name.strip():
            raise AltiumProjectBuildError("project_name cannot be empty.")
        try:
            schematic.validate()
            layout.validate(schematic)
        except Exception as exc:
            raise AltiumProjectBuildError(f"Invalid schematic or layout: {exc}") from exc

        components = [
            AltiumComponent(
                reference=c.reference,
                value=c.value,
                symbol_name=c.symbol_name,
                footprint_name=c.footprint_name,
                manufacturer=c.manufacturer,
                part_number=c.part_number,
                description=c.description,
                fields=dict(c.fields),
                pins=tuple((p.number, p.name, p.electrical_type) for p in c.pins),
            )
            for c in schematic.components
        ]
        nets = [
            AltiumNet(
                name=n.name,
                connections=tuple(
                    AltiumConnection(x.component_reference, x.pin_number)
                    for x in n.connections
                ),
                net_class=n.net_class,
                description=n.description,
            )
            for n in schematic.nets
        ]
        placements = [
            AltiumSymbolPlacement(
                reference=s.reference,
                x_mm=s.position.x,
                y_mm=s.position.y,
                rotation_deg=s.rotation_deg,
                body_width_mm=s.body_width_mm,
                body_height_mm=s.body_height_mm,
            )
            for s in layout.symbols.values()
        ]
        wires = [
            AltiumWire(
                net_name=w.net_name,
                start_x_mm=w.start.x,
                start_y_mm=w.start.y,
                end_x_mm=w.end.x,
                end_y_mm=w.end.y,
            )
            for w in layout.wires
        ]
        combined: Dict[str, Any] = {
            "source": "LLM-PCB",
            "source_design_name": schematic.name,
            "layout_engine": layout.metadata.get("layout_engine", "unknown"),
        }
        combined.update(dict(schematic.metadata))
        combined.update(dict(layout.metadata))
        combined.update(dict(metadata or {}))
        model = AltiumProjectModel(
            project_name=project_name,
            design_name=schematic.name,
            grid_mm=layout.grid_mm,
            components=components,
            nets=nets,
            placements=placements,
            wires=wires,
            metadata=combined,
        )
        model.validate()
        return model
