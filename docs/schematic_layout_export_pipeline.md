# Schematic Layout Export Pipeline

The schematic flow is now separated into three responsibilities:

```text
SchematicDesign
    logical components and nets
        |
        v
BuckSchematicLayoutEngine
    symbol coordinates, pin endpoints, wires,
    junctions, and labels
        |
        v
KiCadSchematicExporter
    `.kicad_sch` serialization only
```

## Tests

```powershell
python -m pytest test/test_buck_schematic_layout.py -v
python -m pytest test/test_kicad_schematic_exporter.py -v
```

## Generate the KiCad schematic

```powershell
python -m examples.export_buck_kicad_schematic
```

Generated file:

```text
output/Buck_24V_to_5V_3A.kicad_sch
```

## Validation in KiCad

Confirm that:

- all nine symbols are visible;
- visible wires are present;
- junctions appear at branches;
- VIN, SW, VOUT, FB, GND, and BOOT labels are visible;
- moving a symbol shows that the existing wires remain editable;
- KiCad can save and reopen the file.

Only after KiCad opens and saves the schematic successfully should it be
tested with the Altium Designer KiCad importer.
