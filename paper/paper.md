
## 3.5 EDA-Neutral Intermediate Representation

The generated schematic graph is serialized into an
EDA-neutral JSON intermediate representation. The
representation contains metadata, components, component
pins, electrical nets, and pin-to-net connections.

The intermediate representation separates the circuit
generation process from vendor-specific EDA file formats.
As a result, the same design representation can be used
by subsequent placement, routing, and export modules.

The current representation also records basic design
statistics, including the numbers of components, pins,
and nets, to support automatic validation and experimental
evaluation.