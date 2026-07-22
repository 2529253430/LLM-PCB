from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.design_ir import UniversalProjectIR

from .component import (
    SchComponent,
    SchPin,
    SchPinElectricalType,
)
from .document import AltiumSchematicDocument
from .label import SchNetLabel
from .primitives import (
    AltiumSchematicModelError,
    SchPoint,
)
from .sheet import SchSheet
from .wire import SchJunction, SchWire


class AltiumSchematicBuildError(
    AltiumSchematicModelError
):
    """Raised when UniversalProjectIR cannot be mapped safely."""


class AltiumSchematicBuilder:
    """Map UniversalProjectIR into the Altium schematic model.

    The builder performs no file I/O. Native SchDoc serialization belongs to
    the Phase 16C writer.
    """

    _ELECTRICAL_TYPE_MAP = {
        "passive": SchPinElectricalType.PASSIVE,
        "input": SchPinElectricalType.INPUT,
        "power_in": SchPinElectricalType.POWER,
        "power_input": SchPinElectricalType.POWER,
        "output": SchPinElectricalType.OUTPUT,
        "power_out": SchPinElectricalType.POWER,
        "power_output": SchPinElectricalType.POWER,
        "bidirectional": SchPinElectricalType.BIDIRECTIONAL,
        "bidi": SchPinElectricalType.BIDIRECTIONAL,
        "open_collector": SchPinElectricalType.OPEN_COLLECTOR,
        "open_emitter": SchPinElectricalType.OPEN_EMITTER,
        "tri_state": SchPinElectricalType.TRI_STATE,
        "tristate": SchPinElectricalType.TRI_STATE,
        "unspecified": SchPinElectricalType.UNSPECIFIED,
    }

    def build_from_ir(
        self,
        project_ir: UniversalProjectIR,
    ) -> AltiumSchematicDocument:
        self._validate_project_ir(project_ir)

        schematic = project_ir.schematic
        symbol_placements = {
            placement.component_id: placement
            for placement in schematic.symbol_placements
        }
        pin_placements = {
            (
                placement.component_id,
                str(placement.pin_number),
            ): placement
            for placement in schematic.pin_placements
        }
        nets_by_id = {
            net.id: net
            for net in project_ir.nets
        }

        components = tuple(
            self._map_component(
                component,
                symbol_placements,
                pin_placements,
            )
            for component in project_ir.components
        )

        wires = tuple(
            SchWire(
                wire_id=f"wire:{index}",
                net_id=wire.net_id,
                vertices=tuple(
                    self._point(point)
                    for point in self._wire_points(wire)
                ),
            )
            for index, wire in enumerate(
                schematic.wires,
                start=1,
            )
        )

        junctions = tuple(
            SchJunction(
                junction_id=f"junction:{index}",
                net_id=junction.net_id,
                location=self._point(junction.position),
            )
            for index, junction in enumerate(
                schematic.junctions,
                start=1,
            )
        )

        labels = self._map_labels(
            project_ir=project_ir,
            nets_by_id=nets_by_id,
            pin_placements=pin_placements,
        )

        metadata = self._document_metadata(project_ir)

        document = AltiumSchematicDocument(
            document_id=(
                f"{project_ir.project_id}:schematic"
            ),
            name=schematic.name,
            sheet=SchSheet(
                name=schematic.name,
                grid_mm=schematic.grid_mm,
                title=project_ir.project_name,
                document_number=str(
                    metadata.get("document_number", "")
                ),
                revision=str(
                    metadata.get("revision", "")
                ),
                company=str(
                    metadata.get("company", "")
                ),
                author=str(
                    metadata.get("author", "")
                ),
            ),
            components=components,
            wires=wires,
            labels=labels,
            junctions=junctions,
            metadata=metadata,
        )
        document.validate()
        return document

    def _map_component(
        self,
        component: Any,
        symbol_placements: Mapping[str, Any],
        pin_placements: Mapping[tuple[str, str], Any],
    ) -> SchComponent:
        placement = symbol_placements.get(component.id)
        if placement is None:
            raise AltiumSchematicBuildError(
                "Missing symbol placement for component "
                f"{component.reference!r} ({component.id!r})."
            )

        pins = tuple(
            self._map_pin(
                component_id=component.id,
                pin=pin,
                pin_placements=pin_placements,
                fallback_location=placement.position,
            )
            for pin in component.pins
        )

        parameters = {
            str(key): str(value)
            for key, value in dict(
                component.parameters or {}
            ).items()
        }
        if component.manufacturer:
            parameters.setdefault(
                "Manufacturer",
                str(component.manufacturer),
            )
        if component.part_number:
            parameters.setdefault(
                "Part Number",
                str(component.part_number),
            )

        return SchComponent(
            component_id=component.id,
            reference=component.reference,
            value=component.value,
            symbol_name=component.symbol_name,
            location=self._point(placement.position),
            pins=pins,
            rotation_deg=int(placement.rotation_deg),
            mirrored=bool(placement.mirrored),
            footprint=component.footprint_name,
            description=component.description,
            parameters=parameters,
        )

    def _map_pin(
        self,
        *,
        component_id: str,
        pin: Any,
        pin_placements: Mapping[tuple[str, str], Any],
        fallback_location: Any,
    ) -> SchPin:
        pin_number = str(pin.number)
        placement = pin_placements.get(
            (component_id, pin_number)
        )
        location = (
            placement.endpoint
            if placement is not None
            else fallback_location
        )

        return SchPin(
            pin_id=(
                f"{component_id}:pin:{pin_number}"
            ),
            name=str(pin.name),
            designator=pin_number,
            location=self._point(location),
            electrical_type=self._electrical_type(
                pin.electrical_type
            ),
        )

    def _map_labels(
        self,
        *,
        project_ir: UniversalProjectIR,
        nets_by_id: Mapping[str, Any],
        pin_placements: Mapping[tuple[str, str], Any],
    ) -> tuple[SchNetLabel, ...]:
        labels: list[SchNetLabel] = []
        labelled_net_ids: set[str] = set()

        for index, label in enumerate(
            project_ir.schematic.labels,
            start=1,
        ):
            net = nets_by_id.get(label.net_id)
            text = str(
                label.text
                or (net.name if net is not None else label.net_id)
            )
            labels.append(
                SchNetLabel(
                    label_id=f"label:{index}",
                    text=text,
                    net_id=label.net_id,
                    location=self._point(label.position),
                    rotation_deg=int(label.rotation_deg),
                )
            )
            labelled_net_ids.add(label.net_id)

        # A logical IR net should remain named even if an adapter did not
        # create an explicit IRNetLabel. Place a deterministic fallback label
        # at the first connected pin, then at the first wire, then at origin.
        wires_by_net: dict[str, list[Any]] = {}
        for wire in project_ir.schematic.wires:
            wires_by_net.setdefault(
                wire.net_id,
                [],
            ).append(wire)

        for net in project_ir.nets:
            if net.id in labelled_net_ids:
                continue

            position = None
            for connection in net.connections:
                placement = pin_placements.get(
                    (
                        connection.component_id,
                        str(connection.pin_number),
                    )
                )
                if placement is not None:
                    position = placement.endpoint
                    break

            if position is None:
                net_wires = wires_by_net.get(net.id, [])
                if net_wires:
                    position = self._wire_points(
                        net_wires[0]
                    )[0]

            labels.append(
                SchNetLabel(
                    label_id=f"label:net:{net.id}",
                    text=net.name,
                    net_id=net.id,
                    location=(
                        self._point(position)
                        if position is not None
                        else SchPoint(0.0, 0.0)
                    ),
                )
            )

        return tuple(labels)

    def _validate_project_ir(
        self,
        project_ir: UniversalProjectIR,
    ) -> None:
        if project_ir is None:
            raise AltiumSchematicBuildError(
                "project_ir cannot be None."
            )
        if project_ir.schematic is None:
            raise AltiumSchematicBuildError(
                "UniversalProjectIR does not contain a schematic."
            )

        validate = getattr(project_ir, "validate", None)
        if callable(validate):
            validation_result = validate()
            if validation_result is False:
                raise AltiumSchematicBuildError(
                    "UniversalProjectIR validation failed."
                )

    def _document_metadata(
        self,
        project_ir: UniversalProjectIR,
    ) -> dict[str, object]:
        metadata: dict[str, object] = {
            str(key): value
            for key, value in dict(
                project_ir.metadata or {}
            ).items()
        }
        metadata.update(
            {
                "source_ir_schema": (
                    "llm-pcb.universal-project-ir"
                ),
                "source_ir_version": (
                    project_ir.schema_version
                ),
                "source_project_id": (
                    project_ir.project_id
                ),
                "source_project_name": (
                    project_ir.project_name
                ),
                "target_eda": "altium",
                "mapping_stage": "phase16b",
            }
        )

        schematic_metadata = dict(
            project_ir.schematic.metadata or {}
        )
        if schematic_metadata:
            metadata["schematic_metadata"] = (
                schematic_metadata
            )

        return metadata

    @classmethod
    def _electrical_type(
        cls,
        value: Any,
    ) -> SchPinElectricalType:
        normalized = str(
            getattr(value, "value", value)
        ).strip().lower()
        return cls._ELECTRICAL_TYPE_MAP.get(
            normalized,
            SchPinElectricalType.UNSPECIFIED,
        )

    @staticmethod
    def _wire_points(wire: Any) -> tuple[Any, ...]:
        """Return wire geometry across supported IRWire representations.

        The current IR implementation may store geometry as a segment object,
        while earlier architecture drafts described direct ``start`` and
        ``end`` attributes. Supporting both keeps the backend mapper decoupled
        from that storage detail.
        """
        vertices = getattr(wire, "vertices", None)
        if vertices is not None:
            points = tuple(vertices)
            if len(points) >= 2:
                return points

        points_value = getattr(wire, "points", None)
        if points_value is not None:
            points = tuple(points_value)
            if len(points) >= 2:
                return points

        segment = getattr(wire, "segment", None)
        if segment is not None:
            start = getattr(segment, "start", None)
            end = getattr(segment, "end", None)
            if start is not None and end is not None:
                return (start, end)

        start = getattr(wire, "start", None)
        end = getattr(wire, "end", None)
        if start is not None and end is not None:
            return (start, end)

        raise AltiumSchematicBuildError(
            "Unsupported IRWire geometry. Expected vertices, points, "
            "segment.start/segment.end, or start/end."
        )

    @staticmethod
    def _point(value: Any) -> SchPoint:
        return SchPoint(
            x_mm=float(value.x_mm),
            y_mm=float(value.y_mm),
        )
