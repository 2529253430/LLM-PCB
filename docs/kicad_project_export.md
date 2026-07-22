# KiCad Project Export

## Architecture

```text
SchematicDesign
        |
SchematicLayout
        |
Existing .kicad_pcb
        |
        v
KiCadProjectExporter
        |
        v
Complete KiCad project directory
```

## Important format detail

A modern `.kicad_pro` file is a JSON settings file. It is not an
S-expression file. The exporter therefore writes valid JSON and allows
KiCad to add additional GUI-specific settings when the project is saved.

## Generated directory

```text
output/projects/Buck_24V_to_5V_3A/
├── Buck_24V_to_5V_3A.kicad_pro
├── Buck_24V_to_5V_3A.kicad_sch
├── Buck_24V_to_5V_3A.kicad_pcb
├── metadata.json
└── validation.json
```

## Run tests

```powershell
python -m pytest test/test_kicad_project_exporter.py -v
```

## Generate the complete project

First ensure that the existing PCB pipeline has generated:

```text
output/Buck_24V_to_5V_3A.kicad_pcb
```

Then run:

```powershell
python -m examples.export_complete_kicad_project
```

## KiCad validation

Open:

```text
output/projects/Buck_24V_to_5V_3A/
Buck_24V_to_5V_3A.kicad_pro
```

Confirm that both the schematic and PCB can be opened from the project.

## Altium import

In Altium Designer:

```text
File
→ Import Wizard
→ KiCad Design Files
```

Select the generated KiCad project files. The KiCad importer extension
must be installed and enabled in Altium Designer.

After import, verify:

- schematic component count;
- PCB component count;
- designators;
- net names;
- schematic-to-PCB relationships;
- footprints;
- routed tracks.
