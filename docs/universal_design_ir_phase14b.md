# Phase 14B: Universal Design IR Core

Phase 14B implements the first executable version of the universal,
technology-neutral LLM-PCB project model.

## Added package

```text
src/design_ir/
├── __init__.py
├── component.py
├── connectivity.py
├── constraints.py
├── geometry.py
├── project.py
├── schematic.py
├── serializer.py
└── validator.py
```

## Current scope

Implemented:

- geometry primitives;
- components and pins;
- nets and pin references;
- schematic placements and wires;
- project-level constraints;
- structured validation reports;
- deterministic JSON serialization.

Deferred:

- PCB board model;
- adapters from existing schematic and PCB classes;
- backend integration;
- native Altium serialization.

## Run tests

```powershell
python -m pytest -q test/test_universal_design_ir.py
```

## Run example

```powershell
python -m examples.export_universal_ir
```

Generated files:

```text
output/universal_ir/Phase14B_Example/
├── project_ir.json
└── project_ir_validation.json
```
