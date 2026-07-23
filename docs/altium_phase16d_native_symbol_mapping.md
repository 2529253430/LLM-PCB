# Phase 16D: Native Symbol Mapping

Phase 16D replaces the generic rectangle-only artwork from Phase 16C with
component-specific native Altium schematic graphics.

## Supported mappings

| Reference / hint | Symbol |
|---|---|
| `R*`, resistor | IEC resistor |
| `C*`, capacitor | capacitor plates |
| `L*`, inductor | four-coil inductor |
| `D*`, diode | diode |
| `J*`, `P*`, connector | connector body |
| `U*`, controller, regulator, IC | IC body |
| other | generic body |

The mapper creates local symbol primitives. The SchDoc writer translates them to
native Altium records:

- `RECORD=12`: arc;
- `RECORD=13`: line;
- `RECORD=14`: rectangle.

This phase changes artwork only. Existing component identity, pins, wires, net
labels and junctions remain unchanged. Topology-aware placement and wire-routing
improvements are deferred to Phases 16E and 16F.

## Tests

```powershell
python -m pytest -q test/test_altium_symbol_mapping.py
python -m pytest -q test/test_altium_schdoc_symbols.py
python -m pytest -q
```

## Symbol gallery

```powershell
python -m examples.export_native_altium_symbols
```

Output:

```text
output/altium_phase16d/Phase16D_Symbols.SchDoc
```

Regenerate the Buck document with the existing Phase 16C example to see mapped
symbols in the complete schematic.
