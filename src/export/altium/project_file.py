from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Mapping, Optional
import hashlib
import re


class AltiumProjectFileError(Exception):
    """Raised when a native Altium project file cannot be generated."""


@dataclass(frozen=True)
class AltiumProjectDocument:
    """One document registered in an Altium PCB project."""

    path: str
    unique_id: Optional[str] = None
    annotation_order: int = -1

    def validate(self) -> None:
        if not self.path.strip():
            raise AltiumProjectFileError(
                "Altium project document path cannot be empty."
            )
        if Path(self.path).is_absolute():
            raise AltiumProjectFileError(
                "Altium project document paths must be relative."
            )
        if self.annotation_order < -1:
            raise AltiumProjectFileError(
                "annotation_order must be -1 or greater."
            )

    @property
    def normalized_path(self) -> str:
        self.validate()
        return str(PureWindowsPath(self.path))

    @property
    def resolved_unique_id(self) -> str:
        if self.unique_id:
            normalized = self.unique_id.strip().upper()
            if not re.fullmatch(r"[A-Z]{8}", normalized):
                raise AltiumProjectFileError(
                    "Document unique_id must contain exactly "
                    "eight uppercase letters."
                )
            return normalized

        digest = hashlib.sha256(
            self.normalized_path.encode("utf-8")
        ).digest()
        return "".join(
            chr(ord("A") + (byte % 26))
            for byte in digest[:8]
        )


@dataclass(frozen=True)
class AltiumProjectFile:
    """Technology-neutral representation of a native .PrjPcb file."""

    project_name: str
    documents: tuple[AltiumProjectDocument, ...] = ()
    parameters: Mapping[str, str] = field(default_factory=dict)
    output_path: str = ""
    log_folder_path: str = ""

    def validate(self) -> None:
        if not self.project_name.strip():
            raise AltiumProjectFileError(
                "Altium project_name cannot be empty."
            )

        seen_paths: set[str] = set()
        seen_ids: set[str] = set()

        for document in self.documents:
            document.validate()

            path_key = document.normalized_path.casefold()
            if path_key in seen_paths:
                raise AltiumProjectFileError(
                    "Duplicate Altium project document path: "
                    f"{document.normalized_path}"
                )
            seen_paths.add(path_key)

            unique_id = document.resolved_unique_id
            if unique_id in seen_ids:
                raise AltiumProjectFileError(
                    "Duplicate Altium document unique id: "
                    f"{unique_id}"
                )
            seen_ids.add(unique_id)


class AltiumPrjPcbWriter:
    """Write an ASCII Altium Designer PCB project file."""

    EXTENSION = ".PrjPcb"

    def write(
        self,
        project: AltiumProjectFile,
        output_directory: str | Path,
        *,
        overwrite: bool = True,
    ) -> Path:
        project.validate()

        destination = Path(output_directory)
        if destination.exists() and not destination.is_dir():
            raise AltiumProjectFileError(
                f"Output path is not a directory: {destination}"
            )
        destination.mkdir(parents=True, exist_ok=True)

        filename = (
            self._safe_filename(project.project_name)
            + self.EXTENSION
        )
        output_path = destination / filename

        if output_path.exists() and not overwrite:
            raise AltiumProjectFileError(
                f"Altium project file already exists: {output_path}"
            )

        try:
            output_path.write_text(
                self.render(project),
                encoding="utf-8",
                newline="\r\n",
            )
        except OSError as exc:
            raise AltiumProjectFileError(
                f"Failed to write {output_path}: {exc}"
            ) from exc

        return output_path

    def render(self, project: AltiumProjectFile) -> str:
        project.validate()

        lines: list[str] = []
        lines.extend(self._design_section(project))
        lines.extend(
            [
                "",
                "[Preferences]",
                "PrefsVaultGUID=",
                "PrefsRevisionGUID=",
            ]
        )

        for index, document in enumerate(
            project.documents,
            start=1,
        ):
            lines.append("")
            lines.extend(
                self._document_section(index, document)
            )

        for index, (name, value) in enumerate(
            sorted(project.parameters.items()),
            start=1,
        ):
            lines.append("")
            lines.extend(
                [
                    f"[Parameter{index}]",
                    f"Name={name}",
                    f"Value={value}",
                ]
            )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _design_section(
        project: AltiumProjectFile,
    ) -> list[str]:
        return [
            "[Design]",
            "Version=1.0",
            "HierarchyMode=0",
            "ChannelRoomNamingStyle=0",
            "ChannelDesignatorFormat=$Component_$RoomName",
            "ChannelRoomLevelSeparator=_",
            "ReorderDocumentsOnCompile=1",
            "NameNetsHierarchically=0",
            "PowerPortNamesTakePriority=0",
            "PushECOToAnnotationFile=1",
            "DItemRevisionGUID=",
            "ReportSuppressedErrorsInMessages=0",
            f"OutputPath={project.output_path}",
            f"LogFolderPath={project.log_folder_path}",
            "ManagedProjectGUID=",
            "IncludeDesignInRelease=0",
        ]

    @staticmethod
    def _document_section(
        index: int,
        document: AltiumProjectDocument,
    ) -> list[str]:
        return [
            f"[Document{index}]",
            f"DocumentPath={document.normalized_path}",
            "AnnotationEnabled=1",
            "AnnotateStartValue=1",
            "AnnotationIndexControlEnabled=0",
            "AnnotateSuffix=",
            "AnnotateScope=All",
            f"AnnotateOrder={document.annotation_order}",
            "DoLibraryUpdate=1",
            "DoDatabaseUpdate=1",
            "ClassGenCCAutoEnabled=1",
            "ClassGenCCAutoRoomEnabled=1",
            "ClassGenNCAutoScope=None",
            "DItemRevisionGUID=",
            "GenerateClassCluster=0",
            f"DocumentUniqueId={document.resolved_unique_id}",
        ]

    @staticmethod
    def _safe_filename(value: str) -> str:
        name = value.strip()
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        name = name.rstrip(". ")
        if not name:
            raise AltiumProjectFileError(
                "project_name does not produce a valid filename."
            )
        return name
