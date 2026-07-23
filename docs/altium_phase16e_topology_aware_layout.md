# Phase 16E: Topology-aware Buck schematic layout

Phase 16E improves the technology-neutral schematic layout before the design is
converted into UniversalProjectIR or serialized as an Altium SchDoc.

## Signal-flow placement

The Buck power path is arranged from left to right:

```text
J1 -> CIN -> U1 -> L1 -> COUT -> J2
```

The feedback divider is stacked vertically beside the output stage, and the
bootstrap capacitor remains close to the regulator switching pins.

## Routing lanes

The layout uses separate logical lanes for:

- the VIN, SW and VOUT power path;
- the FB sense path;
- the GND return path;
- the compact BOOT connection.

This removes the previous global trunk-per-net behavior that caused long wires
to cross component bodies and unrelated labels.

## Pin orientation

- J1 points into the circuit and J2 points out of it;
- U1 VIN and EN are on the left;
- U1 SW, BOOT and FB are on the right;
- U1 GND points toward the ground return;
- resistor and capacitor pin 1 is the power-side terminal;
- resistor and capacitor pin 2 is the return-side terminal.

## Scope

Phase 16E provides topology-aware placement and cleaner routing lanes. Phase
16F will add obstacle-aware orthogonal path optimization, wire crossing
minimization, label collision handling and post-route cleanup.

## Test

```powershell
python -m pytest -q test/test_buck_schematic_layout.py
python -m pytest -q test/test_buck_topology_aware_layout.py
python -m pytest -q
```

## Generate the Altium schematic

```powershell
python -m examples.export_topology_aware_buck_schdoc
```

Output:

```text
output/altium_phase16e/Buck_Phase16E.SchDoc
```
