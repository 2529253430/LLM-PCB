from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from .compound_document import CompoundDocumentReader


@dataclass(frozen=True)
class InspectedRecord:
    index: int
    properties: dict[str, str]

    @property
    def record_type(self) -> int | None:
        value = self.properties.get("RECORD")
        return int(value) if value is not None else None


class AltiumSchDocInspector:
    def streams(self, path: str | Path) -> dict[str, bytes]:
        return CompoundDocumentReader().read(path)

    def records(self, path: str | Path, stream_name: str = "FileHeader") -> tuple[InspectedRecord, ...]:
        stream = self.streams(path)[stream_name]
        records: list[InspectedRecord] = []
        offset = 0
        index = 0
        while offset + 4 <= len(stream):
            length = struct.unpack_from("<I", stream, offset)[0]
            offset += 4
            if offset + length > len(stream):
                raise ValueError("Truncated SchDoc property record.")
            payload = stream[offset:offset + length]
            offset += length
            text = payload.rstrip(b"\x00").decode("utf-8", "replace")
            properties: dict[str, str] = {}
            for field in text.split("|"):
                if "=" in field:
                    key, value = field.split("=", 1)
                    properties[key] = value
            records.append(InspectedRecord(index=index, properties=properties))
            index += 1
        return tuple(records)
