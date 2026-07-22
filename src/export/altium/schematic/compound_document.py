from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Mapping

FREE_SECTOR = 0xFFFFFFFF
END_OF_CHAIN = 0xFFFFFFFE
FAT_SECTOR = 0xFFFFFFFD
NO_STREAM = 0xFFFFFFFF


class CompoundDocumentError(ValueError):
    """Raised when a CFB document cannot be encoded or decoded."""


@dataclass(frozen=True)
class CompoundStream:
    name: str
    data: bytes


class CompoundDocumentWriter:
    """Small deterministic CFB v3 writer for Altium schematic streams.

    The implementation intentionally supports the subset needed by SchDoc:
    one root storage, ordinary streams, 512-byte sectors and 64-byte mini
    sectors. It does not depend on olefile or a platform COM implementation.
    """

    sector_size = 512
    mini_sector_size = 64
    mini_stream_cutoff = 4096

    def write(self, streams: Mapping[str, bytes], output_path: str | Path) -> Path:
        payload = self.render(streams)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def render(self, streams: Mapping[str, bytes]) -> bytes:
        if not streams:
            raise CompoundDocumentError("At least one stream is required.")
        names = tuple(sorted(streams, key=str.casefold))
        if len(names) > 3:
            raise CompoundDocumentError(
                "The Phase 16C writer supports at most three SchDoc streams."
            )
        for name in names:
            if not name or len(name) > 31:
                raise CompoundDocumentError(f"Invalid CFB stream name: {name!r}.")

        regular: list[tuple[str, bytes]] = []
        mini: list[tuple[str, bytes]] = []
        for name in names:
            data = bytes(streams[name])
            (mini if len(data) < self.mini_stream_cutoff else regular).append((name, data))

        sector_payloads: list[bytes] = []
        fat: list[int] = []
        stream_locations: dict[str, tuple[int, int]] = {}

        def allocate_regular(data: bytes) -> int:
            count = max(1, (len(data) + self.sector_size - 1) // self.sector_size)
            start = len(sector_payloads)
            for index in range(count):
                chunk = data[index * self.sector_size:(index + 1) * self.sector_size]
                sector_payloads.append(chunk.ljust(self.sector_size, b"\x00"))
                fat.append(start + index + 1 if index + 1 < count else END_OF_CHAIN)
            return start

        for name, data in regular:
            stream_locations[name] = (allocate_regular(data), len(data))

        mini_fat: list[int] = []
        mini_blob = bytearray()
        for name, data in mini:
            count = max(1, (len(data) + self.mini_sector_size - 1) // self.mini_sector_size)
            start = len(mini_fat)
            for index in range(count):
                chunk = data[index * self.mini_sector_size:(index + 1) * self.mini_sector_size]
                mini_blob.extend(chunk.ljust(self.mini_sector_size, b"\x00"))
                mini_fat.append(start + index + 1 if index + 1 < count else END_OF_CHAIN)
            stream_locations[name] = (start, len(data))

        root_start = END_OF_CHAIN
        root_size = len(mini_blob)
        if mini_blob:
            root_start = allocate_regular(bytes(mini_blob))

        mini_fat_start = END_OF_CHAIN
        mini_fat_sector_count = 0
        if mini_fat:
            raw = b"".join(struct.pack("<I", value) for value in mini_fat)
            raw += struct.pack("<I", FREE_SECTOR) * (
                (-len(mini_fat)) % (self.sector_size // 4)
            )
            mini_fat_start = allocate_regular(raw)
            mini_fat_sector_count = len(raw) // self.sector_size

        entries = [
            self._directory_entry(
                "Root Entry", 5, root_start, root_size,
                child=3 if len(names) == 3 else (1 if names else NO_STREAM),
            )
        ]
        # Match the red-black tree layout used by the supplied Altium files.
        tree = self._tree_links(names)
        for index, name in enumerate(names, start=1):
            left, right = tree.get(index, (NO_STREAM, NO_STREAM))
            start, size = stream_locations[name]
            entries.append(self._directory_entry(name, 2, start, size, left=left, right=right))
        directory = b"".join(entries).ljust(self.sector_size, b"\x00")
        directory_start = allocate_regular(directory)

        # One FAT sector handles this intentionally small phase output.
        if len(fat) + 1 > self.sector_size // 4:
            raise CompoundDocumentError("SchDoc exceeds the Phase 16C single-FAT limit.")
        fat_sector_id = len(sector_payloads)
        fat.append(FAT_SECTOR)
        fat_sector = b"".join(struct.pack("<I", value) for value in fat)
        fat_sector += struct.pack("<I", FREE_SECTOR) * (
            self.sector_size // 4 - len(fat)
        )
        sector_payloads.append(fat_sector)

        header = bytearray(512)
        header[0:8] = bytes.fromhex("D0CF11E0A1B11AE1")
        struct.pack_into("<H", header, 24, 0x003E)
        struct.pack_into("<H", header, 26, 0x0003)
        struct.pack_into("<H", header, 28, 0xFFFE)
        struct.pack_into("<H", header, 30, 9)
        struct.pack_into("<H", header, 32, 6)
        struct.pack_into("<I", header, 40, 0)
        struct.pack_into("<I", header, 44, 1)
        struct.pack_into("<I", header, 48, directory_start)
        struct.pack_into("<I", header, 56, self.mini_stream_cutoff)
        struct.pack_into("<I", header, 60, mini_fat_start)
        struct.pack_into("<I", header, 64, mini_fat_sector_count)
        struct.pack_into("<I", header, 68, END_OF_CHAIN)
        struct.pack_into("<I", header, 72, 0)
        struct.pack_into("<I", header, 76, fat_sector_id)
        for offset in range(80, 512, 4):
            struct.pack_into("<I", header, offset, FREE_SECTOR)
        return bytes(header) + b"".join(sector_payloads)

    @staticmethod
    def _tree_links(names: tuple[str, ...]) -> dict[int, tuple[int, int]]:
        if len(names) == 3:
            return {3: (2, 1)}
        if len(names) == 2:
            return {1: (NO_STREAM, 2)}
        return {}

    @staticmethod
    def _directory_entry(
        name: str,
        object_type: int,
        start_sector: int,
        size: int,
        *,
        left: int = NO_STREAM,
        right: int = NO_STREAM,
        child: int = NO_STREAM,
    ) -> bytes:
        entry = bytearray(128)
        encoded = (name + "\x00").encode("utf-16le")
        entry[:len(encoded)] = encoded
        struct.pack_into("<H", entry, 64, len(encoded))
        entry[66] = object_type
        entry[67] = 1
        struct.pack_into("<III", entry, 68, left, right, child)
        struct.pack_into("<I", entry, 116, start_sector)
        struct.pack_into("<Q", entry, 120, size)
        return bytes(entry)


class CompoundDocumentReader:
    """Read streams from the CFB subset emitted by this project and Altium."""

    def read(self, path: str | Path) -> dict[str, bytes]:
        data = Path(path).read_bytes()
        if data[:8] != bytes.fromhex("D0CF11E0A1B11AE1"):
            raise CompoundDocumentError("Not a CFB compound document.")
        sector_size = 1 << struct.unpack_from("<H", data, 30)[0]
        mini_sector_size = 1 << struct.unpack_from("<H", data, 32)[0]
        directory_start = struct.unpack_from("<I", data, 48)[0]
        mini_cutoff = struct.unpack_from("<I", data, 56)[0]
        mini_fat_start = struct.unpack_from("<I", data, 60)[0]
        mini_fat_count = struct.unpack_from("<I", data, 64)[0]
        fat_count = struct.unpack_from("<I", data, 44)[0]
        fat_ids = [x for x in struct.unpack_from("<109I", data, 76) if x != FREE_SECTOR][:fat_count]

        def sector(sid: int) -> bytes:
            offset = (sid + 1) * sector_size
            return data[offset:offset + sector_size]

        fat: list[int] = []
        for sid in fat_ids:
            fat.extend(struct.unpack("<%dI" % (sector_size // 4), sector(sid)))

        def chain(start: int, table: list[int], fetch) -> bytes:
            chunks, seen, sid = [], set(), start
            while sid not in (FREE_SECTOR, END_OF_CHAIN) and sid not in seen:
                seen.add(sid)
                chunks.append(fetch(sid))
                sid = table[sid]
            return b"".join(chunks)

        directory = chain(directory_start, fat, sector)
        records = []
        for offset in range(0, len(directory), 128):
            entry = directory[offset:offset + 128]
            if len(entry) < 128:
                break
            name_length = struct.unpack_from("<H", entry, 64)[0]
            name = entry[:max(0, name_length - 2)].decode("utf-16le", "replace")
            records.append((name, entry[66], struct.unpack_from("<I", entry, 116)[0], struct.unpack_from("<Q", entry, 120)[0]))
        root = next(item for item in records if item[1] == 5)
        mini_stream = chain(root[2], fat, sector)[:root[3]] if root[2] != END_OF_CHAIN else b""
        mini_fat: list[int] = []
        if mini_fat_count and mini_fat_start != END_OF_CHAIN:
            raw = chain(mini_fat_start, fat, sector)
            mini_fat = list(struct.unpack("<%dI" % (len(raw) // 4), raw))

        result: dict[str, bytes] = {}
        for name, kind, start, size in records:
            if kind != 2:
                continue
            if size < mini_cutoff:
                raw = chain(start, mini_fat, lambda sid: mini_stream[sid * mini_sector_size:(sid + 1) * mini_sector_size])
            else:
                raw = chain(start, fat, sector)
            result[name] = raw[:size]
        return result
