# Phase 12: EDA Backend Abstraction

Phase 12 introduces a technology-neutral export interface above the existing
KiCad exporters. The design pipeline can now select an EDA target by name
without coupling application code to a concrete exporter class.

## Architecture

```text
SchematicDesign + SchematicLayout + PCB artifact
                     |
                ExportRequest
                     |
              BackendRegistry
               /           \
       KiCadBackend     AltiumBackend
             |          (capability placeholder)
   KiCadProjectExporter
                     |
                ExportResult
```

## Built-in backends

- `kicad`: exports and validates a complete native KiCad project.
- `altium`: registered capability placeholder. It returns an explicit
  unsupported result and never creates fake `.SchDoc` or `.PcbDoc` files.

## Basic use

```python
from src.export import ExportRequest, export_design

request = ExportRequest.create(
    project_name="Buck_24V_to_5V_3A",
    output_root="output/projects",
    schematic=schematic,
    layout=layout,
    pcb_source_path=(
        "output/kicad/Buck_24V_to_5V_3A.kicad_pcb"
    ),
    metadata={"topology": "buck"},
)

result = export_design("kicad", request)

if not result.success:
    raise RuntimeError("; ".join(result.errors))
```

`ExportResult` provides the backend name, success state, output directory,
artifacts, file paths, warnings, errors, and backend-specific metadata.

## Extending the registry

Create a class implementing `EDABackend`, then register it:

```python
registry.register(MyBackend())
result = registry.export("my_backend", request)
```

A backend must publish `BackendCapabilities` so callers can inspect support
before attempting an export.
