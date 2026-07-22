from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .project import UniversalProjectIR


@dataclass(frozen=True)
class IRValidationIssue:
    """One structured universal-IR validation issue."""

    severity: str
    code: str
    message: str
    object_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "object_id": self.object_id,
        }


@dataclass
class IRValidationReport:
    """Structured result produced by UniversalProjectValidator."""

    issues: List[IRValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[IRValidationIssue]:
        return [
            issue
            for issue in self.issues
            if issue.severity == "error"
        ]

    @property
    def warnings(self) -> List[IRValidationIssue]:
        return [
            issue
            for issue in self.issues
            if issue.severity == "warning"
        ]

    @property
    def information(self) -> List[IRValidationIssue]:
        return [
            issue
            for issue in self.issues
            if issue.severity == "info"
        ]

    @property
    def valid(self) -> bool:
        return not self.errors

    def add(
        self,
        *,
        severity: str,
        code: str,
        message: str,
        object_id: Optional[str] = None,
    ) -> None:
        self.issues.append(
            IRValidationIssue(
                severity=severity,
                code=code,
                message=message,
                object_id=object_id,
            )
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "information_count": len(self.information),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class UniversalProjectValidator:
    """Deterministic validator for UniversalProjectIR."""

    SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

    def validate(
        self,
        project: UniversalProjectIR,
    ) -> IRValidationReport:
        report = IRValidationReport()

        self._validate_project_identity(project, report)
        component_pins = self._validate_components(
            project,
            report,
        )
        net_ids = self._validate_nets(
            project,
            component_pins,
            report,
        )
        self._validate_schematic(
            project,
            component_pins,
            net_ids,
            report,
        )
        self._validate_constraints(project, report)

        return report

    def require_valid(
        self,
        project: UniversalProjectIR,
    ) -> IRValidationReport:
        report = self.validate(project)
        if not report.valid:
            details = "; ".join(
                f"{issue.code}: {issue.message}"
                for issue in report.errors
            )
            raise ValueError(
                "UniversalProjectIR validation failed: "
                + details
            )
        return report

    def _validate_project_identity(
        self,
        project: UniversalProjectIR,
        report: IRValidationReport,
    ) -> None:
        if not project.project_id.strip():
            report.add(
                severity="error",
                code="PROJECT_ID_EMPTY",
                message="project_id cannot be empty.",
            )
        if not project.project_name.strip():
            report.add(
                severity="error",
                code="PROJECT_NAME_EMPTY",
                message="project_name cannot be empty.",
            )
        if (
            project.schema_version
            not in self.SUPPORTED_SCHEMA_VERSIONS
        ):
            report.add(
                severity="error",
                code="SCHEMA_VERSION_UNSUPPORTED",
                message=(
                    "Unsupported schema version: "
                    f"{project.schema_version}"
                ),
            )

    def _validate_components(
        self,
        project: UniversalProjectIR,
        report: IRValidationReport,
    ) -> Dict[str, set[str]]:
        component_ids: set[str] = set()
        references: set[str] = set()
        component_pins: Dict[str, set[str]] = {}

        for component in project.components:
            try:
                component.validate()
            except ValueError as exc:
                report.add(
                    severity="error",
                    code="COMPONENT_INVALID",
                    message=str(exc),
                    object_id=component.id or None,
                )

            if component.id in component_ids:
                report.add(
                    severity="error",
                    code="COMPONENT_ID_DUPLICATE",
                    message=(
                        f"Duplicate component id: {component.id}"
                    ),
                    object_id=component.id,
                )
            component_ids.add(component.id)

            if component.reference in references:
                report.add(
                    severity="error",
                    code="COMPONENT_REFERENCE_DUPLICATE",
                    message=(
                        "Duplicate component reference: "
                        f"{component.reference}"
                    ),
                    object_id=component.id,
                )
            references.add(component.reference)
            component_pins[component.id] = {
                pin.number for pin in component.pins
            }

        return component_pins

    def _validate_nets(
        self,
        project: UniversalProjectIR,
        component_pins: Dict[str, set[str]],
        report: IRValidationReport,
    ) -> set[str]:
        net_ids: set[str] = set()
        net_names: set[str] = set()
        connected_pins: Dict[Tuple[str, str], str] = {}

        for net in project.nets:
            try:
                net.validate()
            except ValueError as exc:
                report.add(
                    severity="error",
                    code="NET_INVALID",
                    message=str(exc),
                    object_id=net.id or None,
                )

            if net.id in net_ids:
                report.add(
                    severity="error",
                    code="NET_ID_DUPLICATE",
                    message=f"Duplicate net id: {net.id}",
                    object_id=net.id,
                )
            net_ids.add(net.id)

            if net.name in net_names:
                report.add(
                    severity="error",
                    code="NET_NAME_DUPLICATE",
                    message=f"Duplicate net name: {net.name}",
                    object_id=net.id,
                )
            net_names.add(net.name)

            for connection in net.connections:
                pins = component_pins.get(
                    connection.component_id
                )
                if pins is None:
                    report.add(
                        severity="error",
                        code="NET_COMPONENT_UNKNOWN",
                        message=(
                            f"Net {net.name} references unknown "
                            f"component {connection.component_id}."
                        ),
                        object_id=net.id,
                    )
                    continue

                if connection.pin_number not in pins:
                    report.add(
                        severity="error",
                        code="NET_PIN_UNKNOWN",
                        message=(
                            f"Net {net.name} references unknown pin "
                            f"{connection.component_id}."
                            f"{connection.pin_number}."
                        ),
                        object_id=net.id,
                    )

                key = (
                    connection.component_id,
                    connection.pin_number,
                )
                previous_net = connected_pins.get(key)
                if previous_net is not None:
                    report.add(
                        severity="error",
                        code="PIN_MULTIPLE_NETS",
                        message=(
                            f"Pin {connection.component_id}."
                            f"{connection.pin_number} belongs to "
                            f"both {previous_net} and {net.id}."
                        ),
                        object_id=connection.component_id,
                    )
                connected_pins[key] = net.id

        return net_ids

    def _validate_schematic(
        self,
        project: UniversalProjectIR,
        component_pins: Dict[str, set[str]],
        net_ids: set[str],
        report: IRValidationReport,
    ) -> None:
        try:
            project.schematic.validate_local()
        except ValueError as exc:
            report.add(
                severity="error",
                code="SCHEMATIC_INVALID",
                message=str(exc),
            )

        symbol_ids: set[str] = set()
        for placement in project.schematic.symbol_placements:
            if placement.component_id not in component_pins:
                report.add(
                    severity="error",
                    code="SYMBOL_COMPONENT_UNKNOWN",
                    message=(
                        "Symbol placement references unknown "
                        f"component {placement.component_id}."
                    ),
                    object_id=placement.component_id,
                )
            if placement.component_id in symbol_ids:
                report.add(
                    severity="error",
                    code="SYMBOL_PLACEMENT_DUPLICATE",
                    message=(
                        "Duplicate symbol placement for "
                        f"{placement.component_id}."
                    ),
                    object_id=placement.component_id,
                )
            symbol_ids.add(placement.component_id)

        for component_id in component_pins:
            if component_id not in symbol_ids:
                report.add(
                    severity="error",
                    code="SYMBOL_PLACEMENT_MISSING",
                    message=(
                        "Missing symbol placement for "
                        f"{component_id}."
                    ),
                    object_id=component_id,
                )

        pin_placement_keys: set[Tuple[str, str]] = set()
        for placement in project.schematic.pin_placements:
            key = (
                placement.component_id,
                placement.pin_number,
            )
            pins = component_pins.get(placement.component_id)
            if pins is None:
                report.add(
                    severity="error",
                    code="PIN_PLACEMENT_COMPONENT_UNKNOWN",
                    message=(
                        "Pin placement references unknown "
                        f"component {placement.component_id}."
                    ),
                    object_id=placement.component_id,
                )
            elif placement.pin_number not in pins:
                report.add(
                    severity="error",
                    code="PIN_PLACEMENT_PIN_UNKNOWN",
                    message=(
                        "Pin placement references unknown pin "
                        f"{placement.component_id}."
                        f"{placement.pin_number}."
                    ),
                    object_id=placement.component_id,
                )

            if key in pin_placement_keys:
                report.add(
                    severity="error",
                    code="PIN_PLACEMENT_DUPLICATE",
                    message=(
                        "Duplicate pin placement for "
                        f"{placement.component_id}."
                        f"{placement.pin_number}."
                    ),
                    object_id=placement.component_id,
                )
            pin_placement_keys.add(key)

        for component_id, pins in component_pins.items():
            for pin_number in pins:
                key = (component_id, pin_number)
                if key not in pin_placement_keys:
                    report.add(
                        severity="error",
                        code="PIN_PLACEMENT_MISSING",
                        message=(
                            "Missing pin placement for "
                            f"{component_id}.{pin_number}."
                        ),
                        object_id=component_id,
                    )

        for wire in project.schematic.wires:
            if wire.net_id not in net_ids:
                report.add(
                    severity="error",
                    code="WIRE_NET_UNKNOWN",
                    message=(
                        f"Wire references unknown net "
                        f"{wire.net_id}."
                    ),
                    object_id=wire.net_id,
                )

        for junction in project.schematic.junctions:
            if junction.net_id not in net_ids:
                report.add(
                    severity="error",
                    code="JUNCTION_NET_UNKNOWN",
                    message=(
                        "Junction references unknown net "
                        f"{junction.net_id}."
                    ),
                    object_id=junction.net_id,
                )

        for label in project.schematic.labels:
            if label.net_id not in net_ids:
                report.add(
                    severity="error",
                    code="LABEL_NET_UNKNOWN",
                    message=(
                        f"Label references unknown net "
                        f"{label.net_id}."
                    ),
                    object_id=label.net_id,
                )

    def _validate_constraints(
        self,
        project: UniversalProjectIR,
        report: IRValidationReport,
    ) -> None:
        try:
            project.constraints.validate()
        except ValueError as exc:
            report.add(
                severity="error",
                code="CONSTRAINTS_INVALID",
                message=str(exc),
            )
