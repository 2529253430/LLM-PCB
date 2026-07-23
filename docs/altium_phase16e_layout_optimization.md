# Phase 16E Layout Optimization

This iteration replaces global per-net buses with topology-specific local routing.

## Improvements

- VIN, SW, and VOUT remain on a readable left-to-right power path.
- EN is tied to VIN using a short local branch near U1.
- BOOT is routed only between U1 and CBOOT.
- FB uses a local feedback node at the R1/R2 divider.
- GND remains on a separate return rail.
- Connectors and passive components attach orthogonally to their intended lanes.
- A deterministic layout quality scorer reports wire length, crossings, overlaps,
  long wires, and a normalized score.

## Validation

```powershell
python -m pytest -q test/test_buck_schematic_layout.py
python -m pytest -q test/test_buck_topology_aware_layout.py
python -m pytest -q test/test_buck_layout_optimization.py
python -m pytest -q
```

## Generate

```powershell
python -m examples.export_optimized_buck_schdoc
```

Output:

```text
output/altium_phase16e/Buck_Phase16E_Optimized.SchDoc
```
