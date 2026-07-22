from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import struct
from typing import Any


HEADER_TEXT = "Protel for Windows - Schematic Capture Binary File Version 5.0"


@dataclass(frozen=True)
class SchDocRecord:
    record_type: int
    properties: Mapping[str, Any]

    def payload(self) -> bytes:
        items = [("RECORD", self.record_type), *self.properties.items()]
        text = "".join(f"|{name}={_format(value)}" for name, value in items) + "\x00"
        return text.encode("utf-8")


def encode_property_records(records: Iterable[bytes]) -> bytes:
    output = bytearray()
    for payload in records:
        output.extend(struct.pack("<I", len(payload)))
        output.extend(payload)
    return bytes(output)


def make_unique_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXY"
    return "".join(alphabet[value % len(alphabet)] for value in digest[:8])


def _format(value: Any) -> str:
    if isinstance(value, bool):
        return "T" if value else "F"
    if isinstance(value, float):
        return format(value, ".9g")
    return str(value)
