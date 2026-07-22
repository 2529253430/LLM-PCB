# Phase 14A: Universal Design IR Architecture

## 1. Purpose

Phase 14 introduces a technology-neutral project intermediate representation for LLM-PCB.

The goal is to separate:

- circuit and board design intent;
- schematic and PCB geometry;
- design constraints and validation;
- EDA-specific serialization.

After this phase, KiCad, Altium, and future backends should consume the same validated project model.

## 2. Target architecture

```text
Natural-language specification
            |
            v
Topology and design engines
            |
            v
SchematicDesign / SchematicLayout / EDADesign
            |
            v
UniversalProjectIR adapter
            |
            v
UniversalProjectIR
     |             |
     v             v
KiCad backend   Altium backend
```

The first migration step uses adapters. Existing models remain valid while backends gradually move to `UniversalProjectIR`.

## 3. Design principles

### 3.1 Technology neutrality

The IR must not contain:

- KiCad S-expressions;
- Altium record fields;
- backend-specific layer identifiers;
- backend-specific symbol or footprint syntax.

It may contain logical library names and backend mapping hints.

### 3.2 Explicit units

All physical dimensions use millimetres. Angles use degrees. Electrical values preserve their numeric SI values where possible and may also retain the original display text.

### 3.3 Stable identifiers

Human-readable references such as `U1` and `R1` remain first-class fields. Every major IR object also receives a stable internal identifier so references do not depend only on display names.

### 3.4 Validation before serialization

Backends must receive a validated IR. A backend serializer may reject an unsupported feature, but it must not repair an invalid design silently.

### 3.5 Incremental migration

Phase 14 must not break existing KiCad or Altium tests. The existing models remain available during migration:

- `SchematicDesign`;
- `SchematicLayout`;
- existing PCB/EDA design objects;
- `AltiumProjectModel`.

## 4. Package structure

```text
src/design_ir/
├── __init__.py
├── geometry.py
├── component.py
├── connectivity.py
├── schematic.py
├── board.py
├── constraints.py
├── project.py
├── validator.py
└── adapters/
    ├── __init__.py
    ├── schematic_adapter.py
    └── pcb_adapter.py
```

## 5. Core object model

## 5.1 Geometry

### `IRPoint`

```python
@dataclass(frozen=True)
class IRPoint:
    x_mm: float
    y_mm: float
```

### `IRSize`

```python
@dataclass(frozen=True)
class IRSize:
    width_mm: float
    height_mm: float
```

### `IRSegment`

```python
@dataclass(frozen=True)
class IRSegment:
    start: IRPoint
    end: IRPoint
```

### `IRPolygon`

```python
@dataclass(frozen=True)
class IRPolygon:
    points: tuple[IRPoint, ...]
    closed: bool = True
```

## 5.2 Components

### `IRPin`

Required fields:

- `number`;
- `name`;
- `electrical_type`.

Optional fields:

- `swap_group`;
- `function`;
- `metadata`.

### `IRComponent`

Required fields:

- `id`;
- `reference`;
- `value`;
- `symbol_name`;
- `pins`.

Optional fields:

- `footprint_name`;
- `manufacturer`;
- `part_number`;
- `description`;
- `parameters`;
- `metadata`.

No backend-specific symbol record is stored here.

## 5.3 Connectivity

### `IRPinRef`

```python
@dataclass(frozen=True)
class IRPinRef:
    component_id: str
    pin_number: str
```

### `IRNet`

Fields:

- `id`;
- `name`;
- `connections`;
- `net_class`;
- `description`;
- `constraints`;
- `metadata`.

One physical pin may belong to at most one logical net.

## 5.4 Schematic

### `IRSymbolPlacement`

Fields:

- `component_id`;
- `position`;
- `rotation_deg`;
- `body_size`;
- `mirrored`;
- `metadata`.

### `IRPinPlacement`

Fields:

- `component_id`;
- `pin_number`;
- `endpoint`.

### `IRWire`

Fields:

- `net_id`;
- `start`;
- `end`;
- `style`;
- `metadata`.

### `IRJunction`

Fields:

- `net_id`;
- `position`.

### `IRNetLabel`

Fields:

- `net_id`;
- `position`;
- `rotation_deg`;
- `text`.

### `IRSchematic`

Fields:

- `name`;
- `grid_mm`;
- `symbol_placements`;
- `pin_placements`;
- `wires`;
- `junctions`;
- `labels`;
- `metadata`.

## 5.5 Board

Phase 14 establishes the board interfaces without forcing all routing code to migrate immediately.

### `IRBoardOutline`

- polygonal outline;
- optional cutouts;
- unit metadata.

### `IRLayer`

Fields:

- `id`;
- `name`;
- `kind`;
- `order`;
- `copper`;
- `metadata`.

Supported layer kinds initially include:

- signal;
- plane;
- dielectric;
- silkscreen;
- solder mask;
- mechanical.

### `IRFootprintPlacement`

Fields:

- `component_id`;
- `footprint_name`;
- `position`;
- `rotation_deg`;
- `side`;
- `locked`.

### `IRPad`

Fields:

- `component_id`;
- `pad_number`;
- `position`;
- `size`;
- `shape`;
- `layer_ids`;
- `net_id`;
- `drill_mm`.

### `IRTrack`

Fields:

- `net_id`;
- `layer_id`;
- `start`;
- `end`;
- `width_mm`.

### `IRVia`

Fields:

- `net_id`;
- `position`;
- `diameter_mm`;
- `drill_mm`;
- `start_layer_id`;
- `end_layer_id`.

### `IRBoard`

Fields:

- `outline`;
- `layers`;
- `footprints`;
- `pads`;
- `tracks`;
- `vias`;
- `zones`;
- `metadata`.

## 5.6 Constraints

### `IRConstraintSet`

Initial categories:

- minimum track width;
- preferred track width;
- minimum clearance;
- via diameter;
- via drill;
- allowed layers;
- current requirement;
- voltage class;
- differential-pair properties;
- placement restrictions.

Constraints may be attached to:

- the project;
- a net class;
- one net;
- one component;
- one board object.

## 5.7 Project root

### `UniversalProjectIR`

```python
@dataclass
class UniversalProjectIR:
    schema_version: str
    project_id: str
    project_name: str
    schematic: IRSchematic
    board: IRBoard | None
    components: list[IRComponent]
    nets: list[IRNet]
    constraints: IRConstraintSet
    metadata: dict[str, Any]
```

The project root owns logical components and nets. Schematic and board objects reference them by internal identifiers.

## 6. Validation rules

`UniversalProjectValidator` performs deterministic validation.

### Required validation categories

1. Project identity
   - non-empty project name;
   - supported schema version;
   - unique object identifiers.

2. Components
   - unique references;
   - unique pin numbers per component;
   - non-empty value and symbol name.

3. Connectivity
   - every pin reference resolves;
   - no duplicate connection within a net;
   - one pin does not belong to multiple nets;
   - net names are unique.

4. Schematic
   - each component has one symbol placement;
   - each declared pin has a pin placement when a schematic exists;
   - wires reference valid nets;
   - wires are non-zero length;
   - orthogonality is enforced when requested.

5. Board
   - footprint references resolve;
   - pad references resolve;
   - tracks and vias reference valid nets and layers;
   - board dimensions and drill sizes are positive;
   - layer stack identifiers are unique.

6. Constraints
   - numeric constraints are positive;
   - minimum values do not exceed preferred or maximum values;
   - referenced objects and net classes exist.

Validation returns a structured report containing:

- errors;
- warnings;
- information;
- object identifiers;
- rule codes.

## 7. Adapter strategy

## 7.1 Schematic adapter

`SchematicDesignAdapter` converts:

```text
SchematicDesign + SchematicLayout
                |
                v
UniversalProjectIR
```

Mapping:

| Current model | Universal IR |
|---|---|
| `SchematicComponent` | `IRComponent` |
| `SchematicPin` | `IRPin` |
| `SchematicNet` | `IRNet` |
| `PinReference` | `IRPinRef` |
| `SymbolLayout` | `IRSymbolPlacement` |
| `PinLayout` | `IRPinPlacement` |
| `WireSegment` | `IRWire` |
| `Junction` | `IRJunction` |
| `NetLabelLayout` | `IRNetLabel` |

The adapter must preserve metadata and generate deterministic internal IDs.

## 7.2 PCB adapter

A later adapter converts current board objects into `IRBoard`.

The first implementation may support only features already present in LLM-PCB:

- outline;
- component placement;
- pads;
- routed segments;
- vias;
- copper layers.

Unsupported source features must produce warnings rather than being silently discarded.

## 8. Backend migration

## 8.1 Export request

`ExportRequest` will gain:

```python
project_ir: UniversalProjectIR | None = None
```

During migration, it also retains:

```python
schematic
layout
pcb_source_path
```

Resolution order:

1. use `project_ir` when supplied;
2. otherwise build an IR using adapters;
3. preserve the current behavior when a backend has not migrated yet.

## 8.2 KiCad backend

Migration stages:

1. accept `project_ir`;
2. retain existing schematic and PCB serializers;
3. introduce IR-to-KiCad mapping functions;
4. remove direct topology assumptions;
5. keep generated file compatibility tests.

## 8.3 Altium backend

The current `AltiumProjectModel` becomes a backend mapping model.

Future flow:

```text
UniversalProjectIR
        |
        v
AltiumProjectMapper
        |
        v
AltiumProjectModel
        |
        v
Altium serializers
```

The Altium model must no longer be built directly from `SchematicDesign`.

## 9. Compatibility policy

Phase 14 follows these rules:

- no deletion of current public classes;
- no change to existing constructor signatures unless optional;
- no change to current output locations;
- all existing Phase 12 and Phase 13 tests must remain green;
- new IR behavior is covered by separate tests;
- deprecations are documented before removal.

## 10. Serialization

The universal IR must support deterministic JSON serialization.

Proposed files:

```text
project_ir.json
project_ir_validation.json
```

Required serialization properties:

- stable key ordering;
- UTF-8 encoding;
- explicit schema name;
- explicit schema version;
- no Python-specific representations;
- repeatable output for identical input.

Schema name:

```text
llm-pcb.universal-project-ir
```

Initial version:

```text
1.0
```

## 11. Phase 14 implementation plan

### Phase 14A — architecture

Deliverables:

- this architecture document;
- approved object model;
- migration and compatibility rules.

### Phase 14B — core IR

Implement:

- geometry;
- component and net models;
- schematic model;
- project root;
- core validator;
- JSON serialization;
- unit tests.

### Phase 14C — adapters

Implement:

- `SchematicDesignAdapter`;
- `SchematicLayout` mapping;
- project export request integration;
- compatibility tests.

### Phase 14D — backend adoption

Implement:

- Altium mapper consuming `UniversalProjectIR`;
- KiCad backend optional IR input;
- end-to-end equivalence tests.

## 12. Acceptance criteria

Phase 14 is complete when:

1. a Buck schematic and layout convert to `UniversalProjectIR`;
2. validation succeeds without warnings for the reference Buck design;
3. deterministic JSON can be emitted;
4. Altium intermediate output can be generated from the IR;
5. KiCad output remains unchanged for the reference project;
6. all Phase 12 and Phase 13 tests continue to pass;
7. new IR tests pass;
8. no existing public import path is removed.

## 13. Deferred items

The following are intentionally deferred:

- native Altium `SchDoc` serialization;
- native Altium `PcbDoc` serialization;
- EasyEDA serialization;
- hierarchical schematics;
- buses and harnesses;
- differential-pair routing;
- copper pours;
- 3D models;
- simulation models;
- manufacturing panelization.

These features should extend the IR without changing its core identity and connectivity model.
