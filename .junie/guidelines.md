# Junie Guidelines for Future Changes

## Scope

- Apply only minimal, targeted changes required by the task.
- Preserve workspace isolation semantics across API, services, and queries.
- Do not change public API contracts without explicit request.

## Code Style

- Follow the existing project style and naming conventions.
- Keep changes consistent with current module boundaries under `src/rag_system`.
- Avoid adding comments unless the surrounding code already uses them.

## Validation

- For backend logic changes, run relevant tests from `tests/`.
- For API/schema-impacting changes, also update docs in `docs/api.md` and/or `docs/schema.md`.
- Prefer scoped verification first, then broader checks if needed.

## Dependencies and Configuration

- Use `uv` for dependency management (`uv sync --extra dev`).
- Avoid unnecessary dependency additions; justify new packages in PR descriptions.
- Keep environment variable names stable (`RAG_DATABASE_URL`, `RAG_UPLOADS_DIR`, `RAG_EMBEDDING_DIM`).

## Safety Rules

- Never bypass failing tests by weakening assertions or disabling tests.
- Do not commit generated secrets, local `.env` files, or runtime upload artifacts.
- Keep GitHub Actions green for pull requests before merge.

## Documentation

- Always update `README.md` and `docs/` if necessary
