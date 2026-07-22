# Phase 14C: Schematic Adapter for Altium Pipeline

Phase 14C connects the existing schematic design and layout models to the
Universal Design IR.

The project direction is now Altium-first. KiCad export is not part of new
development work.

## Data flow

```text
SchematicDesign
      +
SchematicLayout
      |
      v
SchematicDesignAdapter
      |
      v
UniversalProjectIR
      |
      v
Altium mapping and serialization
```

## Added files

```text
src/design_ir/adapters/
├── __init__.py
└── schematic_adapter.py

test/test_schematic_design_ir_adapter.py
examples/export_altium_ir_adapter.py
```

## Adapter guarantees

- validates the source design and layout;
- generates deterministic component and net identifiers;
- preserves component values, fields, footprint names and metadata;
- converts all schematic geometry into universal IR objects;
- marks the resulting project with `target_eda = altium`;
- validates the generated project before returning it.

## Run tests

```powershell
python -m pytest -q test/test_schematic_design_ir_adapter.py
```

## Run example

```powershell
python -m examples.export_altium_ir_adapter
```

Output:

```text
output/altium_ir/Altium_IR_Adapter/
├── project_ir.json
└── project_ir_validation.json
```

## Next phase

Phase 14D will modify the Altium backend so it consumes
`UniversalProjectIR` directly. Existing KiCad files may remain in the
repository for historical compatibility, but no new KiCad functionality will
be developed.
