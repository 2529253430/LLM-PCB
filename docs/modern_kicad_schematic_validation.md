# Modern KiCad schematic validation

## 1. Run the automated tests

```powershell
python -m pytest test/test_kicad_schematic_exporter.py -v
```

## 2. Generate the schematic

```powershell
python -m examples.export_buck_kicad_schematic
```

Expected output:

```text
output/Buck_24V_to_5V_3A.kicad_sch
```

## 3. Open it in KiCad 10

Use either method:

- double-click the `.kicad_sch` file; or
- open KiCad Schematic Editor, then use File > Open Existing Schematic.

The first validation goal is:

- nine symbols are visible;
- reference designators are visible;
- values are visible;
- VIN, SW, VOUT, FB, GND, and BOOT labels are visible;
- KiCad does not report a parse error.

## 4. Save the file from KiCad

Save it once from KiCad. KiCad may update the file version or formatting.

## 5. Import into Altium Designer

Import the KiCad project or schematic only after KiCad has opened and saved
the file successfully.

The generated symbols are embedded in the schematic. No external `.kicad_sym`
library is required.
