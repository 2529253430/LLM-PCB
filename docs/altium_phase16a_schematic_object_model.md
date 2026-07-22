# Phase 16A: Altium Schematic Object Model

Phase 16A introduces the backend-specific schematic object model used between
the Universal Design IR and the future native SchDoc serializer.

```text
UniversalProjectIR
        ↓
AltiumSchematicBuilder       (Phase 16B)
        ↓
AltiumSchematicDocument      (Phase 16A)
        ↓
Native SchDoc Writer         (Phase 16C)
```

## Scope

This phase adds models for:

- schematic sheets;
- components and pins;
- wires;
- net labels;
- ports;
- junctions;
- free text;
- common geometry primitives.

It deliberately does **not** emit a `.SchDoc` file yet.

## Package

```text
src/export/altium/schematic/
├── __init__.py
├── component.py
├── document.py
├── label.py
├── primitives.py
├── sheet.py
├── wire.py
└── writer.py
```

`AltiumSchematicPreviewWriter` emits deterministic JSON only for inspection and
tests. It must not be described as an Altium-native document writer.

## Validation rules

The model rejects:

- empty IDs and required names;
- non-finite coordinates;
- invalid sheet sizes;
- rotations other than 0, 90, 180, and 270 degrees;
- duplicate object IDs;
- duplicate component references;
- duplicate pin IDs or designators within a component;
- wires with fewer than two vertices;
- zero-length wire segments.

## Test

```powershell
python -m pytest -q test/test_altium_schematic_model.py
python -m pytest -q
```

## Example

```powershell
python -m examples.build_altium_schematic_model
```

The example produces:

```text
output/altium_phase16a/Example.sch-model.json
```

## Next phase

Phase 16B maps `UniversalProjectIR` into
`AltiumSchematicDocument`.
