# Database Schema

## Extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Tables

### `workspaces`

- `id UUID PK`
- `name VARCHAR(255) UNIQUE NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`

### `documents`

- `id UUID PK`
- `workspace_id UUID FK -> workspaces(id) ON DELETE CASCADE`
- `filename VARCHAR(512) NOT NULL`
- `file_type VARCHAR(16) NOT NULL`
- `file_size INTEGER NOT NULL`
- `storage_path VARCHAR(1024) NOT NULL`
- `processing_status document_status NOT NULL`
- `error_message TEXT NULL`
- `total_pages INTEGER NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### `chunks`

- `id UUID PK`
- `workspace_id UUID FK -> workspaces(id) ON DELETE CASCADE`
- `document_id UUID FK -> documents(id) ON DELETE CASCADE`
- `page_number INTEGER NOT NULL`
- `chunk_index INTEGER NOT NULL`
- `content TEXT NOT NULL`
- `embedding VECTOR(384) NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`

Indexes:

- `ix_chunks_workspace_document (workspace_id, document_id)`
- `ix_chunks_embedding_ivfflat` (IVFFLAT with cosine distance)

### `search_history`

- `id UUID PK`
- `workspace_id UUID FK -> workspaces(id) ON DELETE CASCADE`
- `query_text TEXT NOT NULL`
- `results_count INTEGER NOT NULL`
- `success BOOLEAN NOT NULL`
- `error_message TEXT NULL`
- `executed_at TIMESTAMPTZ NOT NULL`

Index:

- `ix_search_history_workspace_executed (workspace_id, executed_at)`

## Data Isolation

Each read/write operation is performed with a mandatory `workspace_id` filter.

- documents are filtered by `documents.workspace_id`
- chunks are filtered by `chunks.workspace_id`
- search is executed only on chunks of the selected workspace
- search history is stored and read only within the workspace
