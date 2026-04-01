const workspaceForm = document.getElementById("workspaceForm");
const workspaceName = document.getElementById("workspaceName");
const workspaceSelect = document.getElementById("workspaceSelect");
const refreshWorkspacesBtn = document.getElementById("refreshWorkspaces");

const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const uploadMessage = document.getElementById("uploadMessage");
const uploadProgressList = document.getElementById("uploadProgressList");
const documentsList = document.getElementById("documentsList");

const searchForm = document.getElementById("searchForm");
const queryInput = document.getElementById("queryInput");
const topKInput = document.getElementById("topKInput");
const resultsBody = document.getElementById("resultsBody");
const historyList = document.getElementById("historyList");
const tabButtons = Array.from(document.querySelectorAll(".tab-button[data-tab-target]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));

const STORAGE_KEY = "activeWorkspaceId";
const TAB_STORAGE_KEY = "activeTabId";
const DOCUMENTS_POLL_INTERVAL_MS = 2000;

let documentsPollingTimerId = null;

function getActiveWorkspaceId() {
    return localStorage.getItem(STORAGE_KEY);
}

function setActiveWorkspaceId(id) {
    localStorage.setItem(STORAGE_KEY, id);
}

function getActiveTabId() {
    return localStorage.getItem(TAB_STORAGE_KEY);
}

function setActiveTabId(id) {
    localStorage.setItem(TAB_STORAGE_KEY, id);
}

function normalizeTabId(tabId) {
    if (tabPanels.some(panel => panel.id === tabId)) {
        return tabId;
    }
    return "searchTab";
}

function activateTab(tabId) {
    const normalizedTabId = normalizeTabId(tabId);

    for (const panel of tabPanels) {
        panel.hidden = panel.id !== normalizedTabId;
    }

    for (const button of tabButtons) {
        const isActive = button.dataset.tabTarget === normalizedTabId;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-selected", String(isActive));
    }
}

async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: {
            ...(options.headers ?? {}),
        },
        ...options,
    });

    if (!response.ok) {
        let message = `Error: ${response.status}`;
        try {
            const body = await response.json();
            if (body.detail) {
                message = body.detail;
            }
        } catch {
            // ignore
        }
        throw new Error(message);
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        return response.json();
    }
    return response;
}

async function loadWorkspaces() {
    const workspaces = await api("/api/workspaces");
    workspaceSelect.innerHTML = "";

    for (const workspace of workspaces) {
        const option = document.createElement("option");
        option.value = workspace.id;
        option.textContent = workspace.name;
        workspaceSelect.append(option);
    }

    const saved = getActiveWorkspaceId();
    if (saved && workspaces.some(item => item.id === saved)) {
        workspaceSelect.value = saved;
    } else if (workspaces.length > 0) {
        workspaceSelect.value = workspaces[0].id;
        setActiveWorkspaceId(workspaces[0].id);
    }

    await refreshWorkspaceData();
}

async function createWorkspace(name) {
    const workspace = await api("/api/workspaces", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name}),
    });
    setActiveWorkspaceId(workspace.id);
    await loadWorkspaces();
}

async function replaceDocument(documentId, file) {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        throw new Error("Select a workspace first");
    }

    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("file", file);

    return api(`/api/documents/${documentId}`, {
        method: "PUT",
        body: formData,
    });
}

async function removeDocument(documentId) {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        throw new Error("Select a workspace first");
    }

    await api(`/api/documents/${documentId}?workspace_id=${workspaceId}`, {
        method: "DELETE",
    });
}

async function loadDocuments() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        documentsList.innerHTML = "";
        setDocumentsPolling(false);
        return;
    }

    const documents = await api(`/api/documents?workspace_id=${workspaceId}`);
    documentsList.innerHTML = "";
    let hasProcessingDocuments = false;

    for (const doc of documents) {
        const li = document.createElement("li");

        const info = document.createElement("span");
        info.textContent = `${doc.filename} — ${doc.processing_status} — pages: ${doc.total_pages}`;
        if (doc.error_message) {
            info.textContent += ` — error: ${doc.error_message}`;
        }
        li.append(info);

        const actions = document.createElement("span");
        actions.className = "document-actions";

        const downloadLink = document.createElement("a");
        downloadLink.href = `/api/documents/${doc.id}/download?workspace_id=${workspaceId}`;
        downloadLink.textContent = "Download";
        downloadLink.target = "_blank";
        downloadLink.rel = "noopener noreferrer";
        actions.append(downloadLink);

        const updateInput = document.createElement("input");
        updateInput.type = "file";
        updateInput.accept = ".pdf,.docx,.txt";
        updateInput.hidden = true;
        updateInput.addEventListener("change", async () => {
            const [selectedFile] = Array.from(updateInput.files ?? []);
            updateInput.value = "";
            if (!selectedFile) {
                return;
            }

            try {
                await replaceDocument(doc.id, selectedFile);
                uploadMessage.textContent = `Document updated: ${selectedFile.name}`;
                await loadDocuments();
            } catch (error) {
                uploadMessage.textContent = error.message;
            }
        });

        const updateButton = document.createElement("button");
        updateButton.type = "button";
        updateButton.textContent = "Update";
        updateButton.addEventListener("click", () => {
            updateInput.click();
        });
        actions.append(updateButton);
        actions.append(updateInput);

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener("click", async () => {
            const confirmed = window.confirm(`Delete document \"${doc.filename}\"?`);
            if (!confirmed) {
                return;
            }

            try {
                await removeDocument(doc.id);
                uploadMessage.textContent = `Document deleted: ${doc.filename}`;
                await loadDocuments();
            } catch (error) {
                uploadMessage.textContent = error.message;
            }
        });
        actions.append(deleteButton);

        li.append(" ");
        li.append(actions);

        if (doc.processing_status === "processing") {
            hasProcessingDocuments = true;
        }
        documentsList.append(li);
    }

    setDocumentsPolling(hasProcessingDocuments);
}

function extractErrorMessage(status, payload) {
    let message = `Error: ${status}`;
    try {
        const body = JSON.parse(payload);
        if (body.detail) {
            message = body.detail;
        }
    } catch {
        // ignore
    }
    return message;
}

async function uploadDocument(file, onProgress) {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        throw new Error("Select a workspace first");
    }

    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("file", file);

    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/documents/upload");

        xhr.upload.addEventListener("progress", event => {
            if (!event.lengthComputable) {
                return;
            }
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent);
        });

        xhr.addEventListener("load", () => {
            if (xhr.status < 200 || xhr.status >= 300) {
                reject(new Error(extractErrorMessage(xhr.status, xhr.responseText)));
                return;
            }
            try {
                const document = JSON.parse(xhr.responseText);
                resolve(document);
            } catch {
                reject(new Error("Failed to parse server response"));
            }
        });

        xhr.addEventListener("error", () => {
            reject(new Error("Network error while uploading file"));
        });

        xhr.send(formData);
    });
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightFragment(text, queryText) {
    const sourceText = String(text ?? "");
    const normalizedQuery = String(queryText ?? "").trim();
    if (!normalizedQuery) {
        return escapeHtml(sourceText);
    }

    const terms = Array.from(new Set(normalizedQuery.split(/\s+/).filter(Boolean)))
        .sort((left, right) => right.length - left.length);
    if (terms.length === 0) {
        return escapeHtml(sourceText);
    }

    const regex = new RegExp(terms.map(escapeRegExp).join("|"), "gi");
    let highlighted = "";
    let lastIndex = 0;

    for (const match of sourceText.matchAll(regex)) {
        const index = match.index ?? 0;
        highlighted += escapeHtml(sourceText.slice(lastIndex, index));
        highlighted += `<mark>${escapeHtml(match[0])}</mark>`;
        lastIndex = index + match[0].length;
    }

    if (lastIndex === 0) {
        return escapeHtml(sourceText);
    }

    highlighted += escapeHtml(sourceText.slice(lastIndex));
    return highlighted;
}

function renderSearchResults(results) {
    resultsBody.innerHTML = "";

    for (const item of results) {
        const row = document.createElement("tr");

        const documentNameCell = document.createElement("td");
        documentNameCell.textContent = item.document_name;
        row.append(documentNameCell);

        const pageNumberCell = document.createElement("td");
        pageNumberCell.textContent = String(item.page_number);
        row.append(pageNumberCell);

        const fragmentCell = document.createElement("td");
        fragmentCell.innerHTML = highlightFragment(item.text, queryInput.value);
        row.append(fragmentCell);

        const similarityCell = document.createElement("td");
        similarityCell.textContent = item.similarity_score.toFixed(4);
        row.append(similarityCell);

        const linkCell = document.createElement("td");
        const link = document.createElement("a");
        link.href = item.document_link;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Open";
        linkCell.append(link);
        row.append(linkCell);

        resultsBody.append(row);
    }
}

async function performSearch(queryText, topK) {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        throw new Error("Select a workspace first");
    }

    const response = await api("/api/search", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            workspace_id: workspaceId,
            query_text: queryText,
            top_k: Number(topK),
        }),
    });

    renderSearchResults(response.results);
    await loadHistory();
}

async function loadHistory() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        historyList.innerHTML = "";
        return;
    }

    const history = await api(`/api/search/history?workspace_id=${workspaceId}&limit=20`);
    historyList.innerHTML = "";

    for (const item of history) {
        const li = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "Rerun";
        button.addEventListener("click", async () => {
            const rerun = await api(`/api/search/history/${item.id}/rerun`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    workspace_id: workspaceId,
                    top_k: Number(topKInput.value || 5),
                }),
            });
            queryInput.value = rerun.query_text;
            renderSearchResults(rerun.results);
            await loadHistory();
        });

        li.textContent = `${new Date(item.executed_at).toLocaleString()} — ${item.query_text} — results: ${item.results_count}`;
        li.append(" ");
        li.append(button);
        historyList.append(li);
    }
}

async function refreshWorkspaceData() {
    await Promise.all([loadDocuments(), loadHistory()]);
}

function setDocumentsPolling(enabled) {
    if (enabled && documentsPollingTimerId === null) {
        documentsPollingTimerId = setInterval(() => {
            refreshWorkspaceData().catch(error => {
                uploadMessage.textContent = error.message;
            });
        }, DOCUMENTS_POLL_INTERVAL_MS);
        return;
    }

    if (!enabled && documentsPollingTimerId !== null) {
        clearInterval(documentsPollingTimerId);
        documentsPollingTimerId = null;
    }
}

workspaceForm.addEventListener("submit", async event => {
    event.preventDefault();
    try {
        await createWorkspace(workspaceName.value.trim());
        workspaceName.value = "";
    } catch (error) {
        uploadMessage.textContent = error.message;
    }
});

workspaceSelect.addEventListener("change", async event => {
    setActiveWorkspaceId(event.target.value);
    await refreshWorkspaceData();
});

refreshWorkspacesBtn.addEventListener("click", async () => {
    try {
        await loadWorkspaces();
    } catch (error) {
        uploadMessage.textContent = error.message;
    }
});

uploadForm.addEventListener("submit", async event => {
    event.preventDefault();
    const files = Array.from(fileInput.files ?? []);
    if (files.length === 0) {
        return;
    }

    const progressRows = files.map(file => {
        const li = document.createElement("li");
        li.textContent = `${file.name} — waiting`;
        uploadProgressList.append(li);
        return li;
    });

    try {
        const uploadedFiles = [];
        uploadProgressList.innerHTML = "";

        for (const [index, file] of files.entries()) {
            const progressRow = progressRows[index];
            uploadProgressList.append(progressRow);
            progressRow.textContent = `${file.name} — uploading 0%`;

            const document = await uploadDocument(file, percent => {
                progressRow.textContent = `${file.name} — uploading ${percent}%`;
            });

            progressRow.textContent = `${file.name} — uploaded, status: ${document.processing_status}`;
            uploadedFiles.push(document.filename);
            uploadMessage.textContent = `Uploaded ${uploadedFiles.length} of ${files.length}`;
        }

        if (uploadedFiles.length === 1) {
            uploadMessage.textContent = `Document uploaded: ${uploadedFiles[0]}`;
        } else {
            uploadMessage.textContent = `Documents uploaded: ${uploadedFiles.length}`;
        }
        await loadDocuments();
        fileInput.value = "";
    } catch (error) {
        uploadMessage.textContent = error.message;
    }
});

searchForm.addEventListener("submit", async event => {
    event.preventDefault();
    try {
        await performSearch(queryInput.value.trim(), topKInput.value);
    } catch (error) {
        uploadMessage.textContent = error.message;
    }
});

for (const button of tabButtons) {
    button.addEventListener("click", () => {
        const tabId = button.dataset.tabTarget;
        if (!tabId) {
            return;
        }

        setActiveTabId(tabId);
        activateTab(tabId);
    });
}

const initialTabId = normalizeTabId(getActiveTabId());
setActiveTabId(initialTabId);
activateTab(initialTabId);

loadWorkspaces().catch(error => {
    uploadMessage.textContent = error.message;
});
