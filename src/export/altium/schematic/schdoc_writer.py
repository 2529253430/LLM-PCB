from __future__ import annotations

from pathlib import Path
from typing import Any

from .compound_document import CompoundDocumentWriter
from .document import AltiumSchematicDocument
from .schdoc_records import HEADER_TEXT, SchDocRecord, encode_property_records, make_unique_id
from .symbols import (
    AltiumSymbolMapper,
    SymbolArc,
    SymbolLine,
    SymbolRectangle,
)


class AltiumSchDocWriteError(ValueError):
    pass


class AltiumSchDocWriter:
    """Serialize the Phase 16A object model as a native binary SchDoc.

    Phase 16D maps logical components to native Altium graphic primitives for
    resistors, capacitors, inductors, diodes, connectors and ICs.
    """

    def write(self, document: AltiumSchematicDocument, output_path: str | Path) -> Path:
        document.validate()
        path = Path(output_path)
        if path.suffix.lower() != ".schdoc":
            raise AltiumSchDocWriteError("Output path must use the .SchDoc extension.")
        records = self._records(document)
        file_header = self._file_header(document, records)
        streams = {
            "FileHeader": file_header,
            "Storage": encode_property_records([b"|HEADER=Icon storage\x00"]),
            "Additional": encode_property_records([
                ("|HEADER=" + HEADER_TEXT + "\x00").encode("ascii")
            ]),
        }
        return CompoundDocumentWriter().write(streams, path)

    def _file_header(self, document: AltiumSchematicDocument, records: list[bytes]) -> bytes:
        header = (
            f"|HEADER={HEADER_TEXT}|Weight={len(records)}|MinorVersion=10"
            f"|UniqueID={make_unique_id(document.document_id)}\x00"
        ).encode("ascii")
        return encode_property_records([header, *records])

    def _records(self, document: AltiumSchematicDocument) -> list[bytes]:
        records: list[bytes] = []
        grid = max(1, round(document.sheet.grid_mm / 0.254))
        records.append(SchDocRecord(31, {
            "FontIdCount": 1,
            "Size1": 10,
            "FontName1": "Times New Roman",
            "UseMBCS": True,
            "IsBOC": True,
            "HotSpotGridOn": True,
            "HotSpotGridSize": grid,
            "SystemFont": 1,
            "BorderOn": True,
            "TitleBlockOn": True,
            "AreaColor": 16317695,
            "SnapGridOn": True,
            "SnapGridSize": grid,
            "VisibleGridOn": True,
            "VisibleGridSize": grid,
            "CustomX": round(document.sheet.size.width_mm / 0.254),
            "CustomY": round(document.sheet.size.height_mm / 0.254),
            "UseCustomSheet": True,
            "Display_Unit": 1,
        }).payload())

        object_index = 0
        for component in document.components:
            owner_index = len(records)
            x, y = self._xy(component.location)
            records.append(SchDocRecord(1, {
                "LibReference": component.symbol_name,
                "ComponentDescription": component.description or component.symbol_name,
                "PartCount": 2,
                "DisplayModeCount": 1,
                "IndexInSheet": object_index,
                "OwnerPartId": -1,
                "Location.X": x,
                "Location.Y": y,
                "CurrentPartId": 1,
                "LibraryPath": "*",
                "SourceLibraryName": "LLM-PCB Generated Symbols",
                "TargetFileName": "*",
                "UniqueID": make_unique_id(component.component_id),
            }).payload())
            object_index += 1

            symbol = AltiumSymbolMapper().resolve(component)
            half_w = round(symbol.body_half_width_mm / 0.254)
            half_h = round(symbol.body_half_height_mm / 0.254)
            for primitive_index, primitive in enumerate(symbol.primitives, start=1):
                records.append(self._symbol_record(
                    owner_index=owner_index,
                    component=component,
                    primitive=primitive,
                    primitive_index=primitive_index,
                ))

            for pin in component.pins:
                px, py = self._xy(pin.location)
                records.append(SchDocRecord(2, {
                    "OwnerIndex": owner_index,
                    "OwnerPartId": 1,
                    "FormalType": 1,
                    "Electrical": self._electrical(pin.electrical_type),
                    "PinConglomerate": self._pin_conglomerate(pin.rotation_deg, pin.hidden),
                    "PinLength": max(1, round(pin.length_mm / 0.254)),
                    "Location.X": px,
                    "Location.Y": py,
                    "Name": pin.name,
                    "Designator": pin.designator,
                    "PinPropagationDelay": "0.000000E+000",
                    "UniqueID": make_unique_id(pin.pin_id),
                }).payload())

            records.append(SchDocRecord(34, {
                "OwnerIndex": owner_index,
                "IndexInSheet": -1,
                "OwnerPartId": -1,
                "Location.X": x - half_w,
                "Location.Y": y + half_h + 8,
                "Color": 8388608,
                "FontID": 1,
                "Text": component.reference,
                "Name": "Designator",
                "ReadOnlyState": 1,
                "UniqueID": make_unique_id(component.component_id + ":designator"),
            }).payload())
            records.append(SchDocRecord(41, {
                "OwnerIndex": owner_index,
                "IndexInSheet": -1,
                "OwnerPartId": -1,
                "Location.X": x - half_w,
                "Location.Y": y - half_h - 12,
                "Color": 8388608,
                "FontID": 1,
                "Text": component.value,
                "Name": "Comment",
                "UniqueID": make_unique_id(component.component_id + ":comment"),
            }).payload())

        for wire in document.wires:
            props: dict[str, Any] = {
                "IndexInSheet": object_index,
                "OwnerPartId": -1,
                "LineWidth": 1,
                "Color": 8388608,
                "UniqueID": make_unique_id(wire.wire_id),
                "LocationCount": len(wire.vertices),
            }
            for index, point in enumerate(wire.vertices, start=1):
                props[f"X{index}"], props[f"Y{index}"] = self._xy(point)
            records.append(SchDocRecord(27, props).payload())
            object_index += 1

        for label in document.labels:
            x, y = self._xy(label.location)
            records.append(SchDocRecord(25, {
                "IndexInSheet": object_index,
                "OwnerPartId": -1,
                "Location.X": x,
                "Location.Y": y,
                "Color": 128,
                "FontID": 1,
                "Text": label.text,
                "Orientation": self._orientation(label.rotation_deg),
                "UniqueID": make_unique_id(label.label_id),
            }).payload())
            object_index += 1

        for junction in document.junctions:
            x, y = self._xy(junction.location)
            records.append(SchDocRecord(29, {
                "IndexInSheet": object_index,
                "OwnerPartId": -1,
                "Location.X": x,
                "Location.Y": y,
                "Color": 128,
            }).payload())
            object_index += 1
        return records

    def _symbol_record(self, *, owner_index, component, primitive, primitive_index) -> bytes:
        origin_x, origin_y = self._xy(component.location)
        unique_id = make_unique_id(
            f"{component.component_id}:symbol:{primitive_index}"
        )

        def local_xy(point):
            x, y = self._xy(point)
            return origin_x + x, origin_y + y

        common = {
            "OwnerIndex": owner_index,
            "IsNotAccesible": True,
            "OwnerPartId": 1,
            "LineWidth": primitive.width,
            "Color": 16711680,
            "UniqueID": unique_id,
        }
        if isinstance(primitive, SymbolLine):
            x1, y1 = local_xy(primitive.start)
            x2, y2 = local_xy(primitive.end)
            return SchDocRecord(13, {
                **common,
                "Location.X": x1,
                "Location.Y": y1,
                "Corner.X": x2,
                "Corner.Y": y2,
            }).payload()
        if isinstance(primitive, SymbolArc):
            x, y = local_xy(primitive.center)
            return SchDocRecord(12, {
                **common,
                "Location.X": x,
                "Location.Y": y,
                "Radius": max(1, round(primitive.radius_mm / 0.254)),
                "StartAngle": primitive.start_angle_deg,
                "EndAngle": primitive.end_angle_deg,
            }).payload()
        if isinstance(primitive, SymbolRectangle):
            x1, y1 = local_xy(primitive.corner_a)
            x2, y2 = local_xy(primitive.corner_b)
            return SchDocRecord(14, {
                **common,
                "Location.X": min(x1, x2),
                "Location.Y": min(y1, y2),
                "Corner.X": max(x1, x2),
                "Corner.Y": max(y1, y2),
                "AreaColor": 11599871,
                "IsSolid": primitive.filled,
            }).payload()
        raise AltiumSchDocWriteError(
            f"Unsupported symbol primitive: {type(primitive).__name__}"
        )

    @staticmethod
    def _xy(point) -> tuple[int, int]:
        return round(point.x_mm / 0.254), round(point.y_mm / 0.254)

    @staticmethod
    def _orientation(rotation: int) -> int:
        return {0: 0, 90: 1, 180: 2, 270: 3}[rotation % 360]

    @staticmethod
    def _pin_conglomerate(rotation: int, hidden: bool) -> int:
        value = {0: 32, 90: 33, 180: 34, 270: 35}[rotation % 360]
        return value | (8 if hidden else 0)

    @staticmethod
    def _electrical(value) -> int:
        name = getattr(value, "value", str(value)).lower()
        return {
            "input": 0,
            "bidirectional": 1,
            "output": 2,
            "open_collector": 3,
            "passive": 4,
            "tri_state": 5,
            "open_emitter": 6,
            "power": 7,
        }.get(name, 4)
