# Phase 16B: Universal IR to Altium Schematic Mapping

Phase 16B connects the technology-neutral project IR to the Altium schematic
object model introduced in Phase 16A.

```text
UniversalProjectIR
        |
        v
AltiumSchematicBuilder
        |
        v
AltiumSchematicDocument
```

The builder performs no file I/O and does not serialize native Altium records.

## Mapping

| Universal IR | Altium schematic model |
|---|---|
| `IRComponent` | `SchComponent` |
| `IRPin` | `SchPin` |
| `IRSymbolPlacement` | component position, rotation, mirror |
| `IRPinPlacement` | pin endpoint |
| `IRWire` | `SchWire` |
| `IRJunction` | `SchJunction` |
| `IRNetLabel` | `SchNetLabel` |
| `IRNet` without an explicit label | deterministic fallback `SchNetLabel` |
| project and schematic metadata | document and sheet metadata |

## Electrical pin types

The builder maps common IR values such as:

- `passive`;
- `input`;
- `output`;
- `bidirectional`;
- `power_in`;
- `power_out`;
- `open_collector`;
- `open_emitter`;
- `tri_state`.

Unknown types become `SchPinElectricalType.UNSPECIFIED`.

## Net labels

Explicit `IRNetLabel` objects are preserved. If a logical net has no explicit
label, the builder creates one at:

1. its first connected pin endpoint;
2. otherwise its first wire start;
3. otherwise `(0, 0)`.

This guarantees that logical net names survive the mapping stage.

## Validation

`build_from_ir()` validates the resulting `AltiumSchematicDocument` before
returning it. Missing symbol placements are treated as build errors rather than
being repaired silently.

## Test

```powershell
python -m pytest -q test/test_altium_schematic_builder.py
python -m pytest -q
```

## Example

```powershell
python -m examples.build_altium_schematic_from_ir
```

Output:

```text
output/altium_phase16b/Buck_Phase16B.sch-model.json
```

The preview remains diagnostic JSON. Native `.SchDoc` serialization begins in
Phase 16C.
