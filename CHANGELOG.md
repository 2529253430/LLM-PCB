# Changelog

All notable changes to the LLM-PCB project are documented here.

---

## Milestone 1 - Knowledge-driven Schematic Generation

### Completed

- SQLite component database
- JSON knowledge base
- Constraint graph
- Knowledge graph enrichment
- Rule engine
- Candidate component selection
- Schematic graph generation
- Schematic JSON export
- Topology-aware PCB placement
- Placement JSON export
- Placement visualization
- Placement validation

### GitHub

Current branch: main

### Paper

Completed Sections

- 3.1 Knowledge Enrichment
- 3.2 Rule Injection
- 3.3 Candidate Selection
- 3.4 Schematic Graph
- 3.5 JSON Intermediate Representation
- 3.6 Topology-aware Placement

---

## Milestone 2 - Constraint-aware Routing

### Completed

- Routing endpoint representation
- Net routing plan representation
- Routing-rule extraction
- Net priority assignment
- Trace-width assignment
- Layer preference assignment
- Avoidance constraint assignment
- Horizontal-first and vertical-first strategy selection
- Routing plan JSON export
- Manhattan geometry routing
- Route point and route segment representation
- Multi-terminal star routing
- Routing result JSON export
- Placement and routing visualization
- Routing-length calculation

### In Progress

- Component obstacle avoidance
- Route intersection detection
- Feedback-net isolation
- A* routing

## Milestone 3 - Obstacle-Aware Routing

### Completed

- Axis-aligned rectangle geometry
- PCB component obstacle representation
- Placement-to-obstacle conversion
- Horizontal segment collision detection
- Vertical segment collision detection
- Trace-width-aware obstacle expansion
- Clearance-aware obstacle generation
- Source and target obstacle exclusion
- Horizontal upper/lower detour generation
- Vertical left/right detour generation
- Candidate collision validation
- Manhattan-length-based detour selection
- Secondary-obstacle candidate rejection
- Initial integration with Manhattan routing
- Controlled obstacle-routing benchmark
- Naive versus obstacle-aware comparison
- Collision-status evaluation
- Routing-length evaluation
- Segment-count evaluation
- Benchmark JSON result export
- Benchmark figure generation

### In Progress

- Multi-obstacle detour routing
- Bent-path obstacle avoidance
- Route intersection detection
- A* routing

## Milestone 5 - EDA Export Preparation

### Completed

- Project goal locked
- KiCad-compatible export path selected
- Real component-library schema
- Physical-pin and logical-role mapping
- TPS5430 initial symbol definition
- Component-library validation

### In Progress

- Footprint and pad model
- Pin-level schematic regeneration
- KiCad schematic export
- KiCad PCB export
- Altium Designer import validation