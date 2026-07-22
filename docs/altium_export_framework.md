# Phase 13: Altium Export Framework

Phase 13 introduces an Altium-oriented intermediate representation.

The generated package contains:

- `altium_project_model.json`
- `manifest.json`

This package is deliberately not presented as a native Altium project and cannot yet be opened directly in Altium Designer.

## Architecture

```text
SchematicDesign + SchematicLayout
              |
              v
    AltiumProjectBuilder
              |
              v
     AltiumProjectModel
              |
              v
 AltiumIntermediateWriter
```

## Run

```powershell
python -m examples.export_altium_intermediate
```

## Test

```powershell
python -m pytest -q test/test_altium_export_framework.py
```
