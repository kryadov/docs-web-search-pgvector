import pytest

from rag_system.validators import ensure_supported_extension, ensure_workspace_scope, extract_extension


def test_extract_extension_lowercases_value() -> None:
    assert extract_extension("Report.PDF") == ".pdf"


def test_ensure_supported_extension_raises_for_invalid_type() -> None:
    with pytest.raises(ValueError):
        ensure_supported_extension("notes.md", (".pdf", ".docx", ".txt"))


def test_ensure_workspace_scope_blocks_cross_project_access() -> None:
    with pytest.raises(ValueError):
        ensure_workspace_scope("workspace-a", "workspace-b")
