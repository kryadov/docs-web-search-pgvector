from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_upload_input_supports_multiple_selection() -> None:
    index_html = (PROJECT_ROOT / "src" / "rag_system" / "static" / "index.html").read_text(encoding="utf-8")

    assert 'id="fileInput"' in index_html
    assert "multiple" in index_html


def test_upload_script_processes_all_selected_files() -> None:
    app_js = (PROJECT_ROOT / "src" / "rag_system" / "static" / "app.js").read_text(encoding="utf-8")

    assert "Array.from(fileInput.files ?? [])" in app_js
    assert "for (const [index, file] of files.entries())" in app_js


def test_upload_ui_has_progress_container() -> None:
    index_html = (PROJECT_ROOT / "src" / "rag_system" / "static" / "index.html").read_text(encoding="utf-8")

    assert 'id="uploadProgressList"' in index_html


def test_ui_uses_tabs_and_search_tab_is_first() -> None:
    index_html = (PROJECT_ROOT / "src" / "rag_system" / "static" / "index.html").read_text(encoding="utf-8")

    search_pos = index_html.index('data-tab-target="searchTab"')
    workspaces_pos = index_html.index('data-tab-target="workspacesTab"')
    upload_pos = index_html.index('data-tab-target="uploadTab"')

    assert search_pos < workspaces_pos < upload_pos


def test_tab_panels_exist_for_search_workspaces_and_upload() -> None:
    index_html = (PROJECT_ROOT / "src" / "rag_system" / "static" / "index.html").read_text(encoding="utf-8")

    assert 'id="searchTab"' in index_html
    assert 'id="workspacesTab"' in index_html
    assert 'id="uploadTab"' in index_html


def test_upload_script_tracks_progress_and_refreshes_document_statuses() -> None:
    app_js = (PROJECT_ROOT / "src" / "rag_system" / "static" / "app.js").read_text(encoding="utf-8")

    assert "new XMLHttpRequest()" in app_js
    assert "xhr.upload.addEventListener(\"progress\"" in app_js
    assert "setInterval" in app_js


def test_script_initializes_tab_state_with_search_fallback() -> None:
    app_js = (PROJECT_ROOT / "src" / "rag_system" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'const TAB_STORAGE_KEY = "activeTabId"' in app_js
    assert 'return "searchTab";' in app_js
    assert "const initialTabId = normalizeTabId(getActiveTabId());" in app_js


def test_search_fragment_uses_highlight_function() -> None:
    app_js = (PROJECT_ROOT / "src" / "rag_system" / "static" / "app.js").read_text(encoding="utf-8")

    assert "function highlightFragment(text, queryText)" in app_js
    assert "<mark>" in app_js
    assert "fragmentCell.innerHTML = highlightFragment(item.text, queryInput.value);" in app_js


def test_search_result_rendering_escapes_untrusted_content() -> None:
    app_js = (PROJECT_ROOT / "src" / "rag_system" / "static" / "app.js").read_text(encoding="utf-8")

    assert "function escapeHtml(value)" in app_js
    assert "documentNameCell.textContent = item.document_name;" in app_js


def test_documents_list_has_download_update_delete_actions() -> None:
    app_js = (PROJECT_ROOT / "src" / "rag_system" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'downloadLink.textContent = "Download"' in app_js
    assert 'updateButton.textContent = "Update"' in app_js
    assert 'deleteButton.textContent = "Delete"' in app_js
    assert "replaceDocument(" in app_js
    assert "removeDocument(" in app_js


def test_static_files_do_not_contain_cyrillic_text() -> None:
    static_files = [
        PROJECT_ROOT / "src" / "rag_system" / "static" / "index.html",
        PROJECT_ROOT / "src" / "rag_system" / "static" / "app.js",
        PROJECT_ROOT / "src" / "rag_system" / "static" / "styles.css",
    ]

    for static_file in static_files:
        content = static_file.read_text(encoding="utf-8")
        assert re.search(r"[А-Яа-яЁё]", content) is None
