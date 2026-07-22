# Phase 16C: Native Altium SchDoc writer

Phase 16C adds a dependency-free writer for the native Altium schematic
container and its property-list records.

## Confirmed from the supplied references

Both `Empty.SchDoc` and `Minimal.SchDoc` are CFB v3 compound documents with
three streams:

- `FileHeader`;
- `Storage`;
- `Additional`.

`FileHeader` is a sequence of little-endian 32-bit lengths followed by
null-terminated property lists. The minimal reference contains native records
for a component (`1`), pins (`2`), wire (`27`), power port (`17`) and junction
(`29`). Phase 16C emits net labels with record `25`.

## Scope

The writer emits:

- sheet record;
- generic rectangular component symbols;
- pins;
- designator and value parameters;
- wires;
- net labels;
- junctions.

Detailed symbol artwork and library resolution are deferred. Components are
therefore electrically represented but use a generated rectangular body.

## Commands

```powershell
python -m pytest -q test/test_altium_schdoc_writer.py
python -m pytest -q
python -m examples.export_native_altium_schdoc
```

The final acceptance check must be performed in the user's installed Altium
Designer version. Structural tests prove that the output is a valid CFB SchDoc
and that expected records can be parsed back; they cannot replace Altium's own
loader validation.
