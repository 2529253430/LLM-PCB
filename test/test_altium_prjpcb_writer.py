from __future__ import annotations

from pathlib import Path

import pytest

from src.export.altium import (
    AltiumPrjPcbWriter,
    AltiumProjectDocument,
    AltiumProjectFile,
    AltiumProjectFileError,
)


def test_writer_creates_native_project_shell(
    tmp_path: Path,
) -> None:
    project = AltiumProjectFile(
        project_name="Buck_24V_to_5V_3A",
        parameters={
            "ProjectName": "Buck_24V_to_5V_3A",
            "LLMPCBIRVersion": "1.0",
        },
    )

    path = AltiumPrjPcbWriter().write(
        project,
        tmp_path,
    )

    assert path.name == "Buck_24V_to_5V_3A.PrjPcb"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("[Design]\n")
    assert "[Preferences]" in text
    assert "[Document1]" not in text
    assert "Name=LLMPCBIRVersion" in text
    assert "Value=1.0" in text


def test_writer_registers_relative_documents(
    tmp_path: Path,
) -> None:
    project = AltiumProjectFile(
        project_name="Example",
        documents=(
            AltiumProjectDocument("Example.SchDoc"),
            AltiumProjectDocument(
                r"PCB\Example.PcbDoc",
                annotation_order=0,
            ),
        ),
    )

    path = AltiumPrjPcbWriter().write(
        project,
        tmp_path,
    )
    text = path.read_text(encoding="utf-8")

    assert "[Document1]" in text
    assert "DocumentPath=Example.SchDoc" in text
    assert "[Document2]" in text
    assert r"DocumentPath=PCB\Example.PcbDoc" in text
    assert text.count("DocumentUniqueId=") == 2


def test_document_ids_are_deterministic() -> None:
    first = AltiumProjectDocument(
        "Example.SchDoc"
    ).resolved_unique_id
    second = AltiumProjectDocument(
        "Example.SchDoc"
    ).resolved_unique_id

    assert first == second
    assert len(first) == 8
    assert first.isalpha()
    assert first.isupper()


def test_writer_rejects_absolute_document_path(
    tmp_path: Path,
) -> None:
    project = AltiumProjectFile(
        project_name="Example",
        documents=(
            AltiumProjectDocument(
                str(tmp_path / "Example.SchDoc")
            ),
        ),
    )

    with pytest.raises(AltiumProjectFileError):
        AltiumPrjPcbWriter().write(project, tmp_path)


def test_writer_honors_overwrite_false(
    tmp_path: Path,
) -> None:
    project = AltiumProjectFile(
        project_name="Example",
    )
    writer = AltiumPrjPcbWriter()
    writer.write(project, tmp_path)

    with pytest.raises(AltiumProjectFileError):
        writer.write(
            project,
            tmp_path,
            overwrite=False,
        )
