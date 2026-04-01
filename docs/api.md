# API

Base prefix: `/api`

## Workspaces

### `POST /workspaces`

Create a workspace.

Request:

```json
{
  "name": "Legal Docs"
}
```

Response `201`:

```json
{
  "id": "uuid",
  "name": "Legal Docs",
  "created_at": "2026-04-02T00:00:00Z"
}
```

### `GET /workspaces`

List all workspaces.

### `POST /workspaces/select`

Validate selection of the active workspace.

Request:

```json
{
  "workspace_id": "uuid"
}
```

## Documents

### `POST /documents/upload`

Upload a file to a specific workspace.

The endpoint accepts exactly one file per request. In the built-in web UI, multi-select upload is implemented as a sequence of requests to this endpoint.

`multipart/form-data`:

- `workspace_id` (`UUID`)
- `file` (`PDF|DOCX|TXT`)

Response `201`:

```json
{
  "id": "uuid",
  "workspace_id": "uuid",
  "filename": "policy.pdf",
  "file_type": ".pdf",
  "file_size": 123456,
  "processing_status": "processing",
  "error_message": null,
  "total_pages": 0,
  "created_at": "2026-04-02T00:00:00Z"
}
```

### `GET /documents?workspace_id=<uuid>`

List documents inside a workspace.

### `GET /documents/{document_id}/status?workspace_id=<uuid>`

Document processing status.

### `GET /documents/{document_id}/download?workspace_id=<uuid>`

Secure document download within a workspace.

### `PUT /documents/{document_id}`

Replace an existing document file inside the same workspace.

`multipart/form-data`:

- `workspace_id` (`UUID`)
- `file` (`PDF|DOCX|TXT`)

Response `200`:

```json
{
  "id": "uuid",
  "workspace_id": "uuid",
  "filename": "policy_v2.pdf",
  "file_type": ".pdf",
  "file_size": 123999,
  "processing_status": "processing",
  "error_message": null,
  "total_pages": 0,
  "created_at": "2026-04-02T00:00:00Z"
}
```

### `DELETE /documents/{document_id}?workspace_id=<uuid>`

Delete a document within a workspace.

Response `204` with empty body.

## Search

### `POST /search`

Request:

```json
{
  "workspace_id": "uuid",
  "query_text": "contract termination terms",
  "top_k": 5
}
```

Response:

```json
{
  "query_text": "contract termination terms",
  "workspace_id": "uuid",
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_name": "contract.pdf",
      "page_number": 3,
      "text": "...",
      "similarity_score": 0.83,
      "document_link": "/api/documents/<id>/download?workspace_id=<workspace-id>"
    }
  ]
}
```

## Search History

### `GET /search/history?workspace_id=<uuid>&limit=20`

Returns the search query history for the current workspace.

### `POST /search/history/{history_id}/rerun`

Re-runs a query from history.

Request:

```json
{
  "workspace_id": "uuid",
  "top_k": 5
}
```

## Isolation Guarantees

- All operations require `workspace_id`.
- Any access to a document/history record verifies ownership within the specified workspace.
- The `pgvector` search index is queried only with the `workspace_id` filter.
