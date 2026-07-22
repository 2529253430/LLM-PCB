# Phase 14D: Altium Backend Adopts UniversalProjectIR

Phase 14D makes `UniversalProjectIR` the canonical input of the Altium
backend.

## New canonical flow

```text
Design engine
     |
     v
SchematicDesign + SchematicLayout
     |
     v
SchematicDesignAdapter
     |
     v
UniversalProjectIR
     |
     v
AltiumProjectBuilder.build_from_ir()
     |
     v
AltiumProjectModel
     |
     v
AltiumIntermediateWriter
```

## Compatibility

The old backend request remains supported:

```python
ExportRequest.create(
    project_name="Buck",
    output_root="output",
    schematic=schematic,
    layout=layout,
)
```

The Altium backend converts those objects through
`SchematicDesignAdapter`.

The preferred request is:

```python
ExportRequest.create(
    project_name=project_ir.project_name,
    output_root="output",
    project_ir=project_ir,
)
```

When both forms are provided, `project_ir` takes precedence.

## Modified files

```text
src/export/backend.py
src/export/altium/builder.py
src/export/altium_backend.py
```

## Added files

```text
test/test_altium_ir_backend.py
examples/export_altium_from_ir.py
docs/universal_design_ir_phase14d.md
```

## Validation

The Altium backend validates the universal IR before mapping it and records
the structured report in `ExportResult.metadata["ir_validation"]`.

## Run tests

```powershell
python -m pytest -q test/test_altium_ir_backend.py
python -m pytest -q
```

## Run example

```powershell
python -m examples.export_altium_from_ir
```

## Expected output

```text
output/altium_from_ir/Buck_24V_to_5V_3A/
├── altium_project_model.json
└── manifest.json
```

These artifacts remain an intermediate package. Native Altium documents are
the next development stage.
