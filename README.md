# docs-web-search-pgvector

A workspace-isolated RAG document search system built on top of `PostgreSQL + pgvector`.

## Stack

- Python `3.14`
- `uv` for environment and dependency management
- FastAPI backend + static UI
- PostgreSQL + `vector` extension (`pgvector`)

## Install `uv`

Install `uv` before running the project setup.

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS/Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your terminal and verify:

```powershell
uv --version
```

## Quick Start

1. Install Python 3.14 and `uv`.
2. Start PostgreSQL and create the `rag_search` database:

```powershell
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE rag_search;"
```

3. Enable `pgvector` in the target database:

```powershell
psql -U postgres -h localhost -p 5432 -d rag_search -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If PostgreSQL runs on another host/port or with another user, adjust `-h`, `-p`, and `-U` accordingly.

4. Install dependencies:

```powershell
uv sync --extra dev
```

5. Optionally configure environment variables:

Copy the example file and adjust values:

```powershell
Copy-Item .env.example .env
```

Then configure via `.env` and/or ENV:

- `RAG_DATABASE_URL` (default: `postgresql+asyncpg://postgres:postgres@localhost:5432/rag_search`)
- `RAG_UPLOADS_DIR` (default: `data/uploads`)
- `RAG_EMBEDDING_DIM` (default: `384`)
- `HOST` (default: `127.0.0.1`)
- `PORT` (default: `8000`)
- `LOG_LEVEL` (default: `info`)

6. Run the service:

```powershell
uv run python -m rag_system.main
```

Or use startup scripts:

```powershell
.\run_service_windows.bat
```

```bash
./run_service_linux.sh
```

7. Open the UI: `http://127.0.0.1:8000`.

## Start with Docker Compose (one click)

Run PostgreSQL + pgvector and the app with a single command:

```powershell
docker compose up --build
```

Then open `http://127.0.0.1:8000`.

Notes:

- PostgreSQL starts from `pgvector/pgvector:pg16`.
- `vector` extension is created automatically from `docker/initdb/01_pgvector.sql`.
- The app uses `RAG_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/rag_search` inside Compose network.
- Docker runtime can be configured via `HOST`, `PORT`, and `LOG_LEVEL` environment variables.

Useful commands:

```powershell
docker compose down
docker compose down -v
docker compose logs -f app
docker compose logs -f postgres
```

## Implemented Features

- Workspace/project management API.
- Tabbed UI with separate sections for search, workspaces, and document upload (search tab is first by default).
- PDF/DOCX/TXT upload to a selected workspace (including multi-select upload in UI).
- Document management actions in upload tab: download, update (replace file), and delete.
- Interactive upload progress in UI for each selected file, plus aggregated status while batch upload is running.
- Automatic UI refresh for document processing statuses after page reload while background processing is still running.
- Static UI (`src/rag_system/static`) uses English-language labels and messages.
- Asynchronous document pipeline: text extraction, logical pages, chunks, embeddings.
- Similarity search via `pgvector`, scoped to the current workspace only.
- Search history storage and repeat query execution.

## Documentation

- `docs/schema.md` — database schema.
- `docs/api.md` — API reference.
