import uuid
import logging
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_system.config import settings
from rag_system.database import SessionLocal, get_db
from rag_system.models import Chunk, Document, DocumentStatus, SearchHistory, Workspace
from rag_system.schemas import (
    DocumentResponse,
    RerunSearchRequest,
    SearchHistoryItem,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceSelectRequest,
)
from rag_system.services.embedding import HashEmbeddingService
from rag_system.services.processing import process_document
from rag_system.services.workspace import ensure_document_in_workspace, ensure_workspace
from rag_system.validators import ensure_supported_extension


embedder = HashEmbeddingService(settings.embedding_dim)
api_router = APIRouter(prefix="/api", tags=["rag"])
logger = logging.getLogger(__name__)

_FRAGMENT_RADIUS = 140


def _extract_search_terms(query_text: str) -> list[str]:
    unique_terms = {term for term in re.split(r"\s+", query_text.lower().strip()) if term}
    return sorted(unique_terms, key=len, reverse=True)


def _slice_fragment(text: str, start: int, end: int, radius: int = _FRAGMENT_RADIUS) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    fragment = text[left:right].strip()
    if left > 0:
        fragment = f"…{fragment}"
    if right < len(text):
        fragment = f"{fragment}…"
    return fragment


def _build_search_fragment(chunk_text: str, query_text: str) -> tuple[str, bool]:
    text = chunk_text.strip()
    if not text:
        return "", False

    lowered_text = text.lower()
    exact_query = query_text.strip().lower()
    if exact_query:
        exact_start = lowered_text.find(exact_query)
        if exact_start >= 0:
            exact_end = exact_start + len(exact_query)
            return _slice_fragment(text, exact_start, exact_end), True

    for term in _extract_search_terms(query_text):
        match_start = lowered_text.find(term)
        if match_start >= 0:
            match_end = match_start + len(term)
            return _slice_fragment(text, match_start, match_end), True

    fallback_limit = min(len(text), _FRAGMENT_RADIUS * 2)
    fallback = text[:fallback_limit].strip()
    if fallback_limit < len(text):
        fallback = f"{fallback}…"
    return fallback, False


def _to_workspace_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
    )


def _to_document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        workspace_id=document.workspace_id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        processing_status=document.processing_status,
        error_message=document.error_message,
        total_pages=document.total_pages,
        created_at=document.created_at,
    )


def _validate_upload_size(payload_size: int) -> None:
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if payload_size > max_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Слишком большой файл")


def _store_document_file(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    extension: str,
    payload: bytes,
) -> Path:
    workspace_dir = settings.uploads_dir / str(workspace_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    stored_path = workspace_dir / f"{document_id}{extension}"
    stored_path.write_bytes(payload)
    return stored_path


@api_router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(request: WorkspaceCreateRequest, session: AsyncSession = Depends(get_db)) -> WorkspaceResponse:
    existing = await session.scalar(select(Workspace).where(Workspace.name == request.name.strip()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace с таким именем уже существует")

    workspace = Workspace(name=request.name.strip())
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return _to_workspace_response(workspace)


@api_router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(session: AsyncSession = Depends(get_db)) -> list[WorkspaceResponse]:
    workspaces = (await session.scalars(select(Workspace).order_by(Workspace.created_at))).all()
    return [_to_workspace_response(workspace) for workspace in workspaces]


@api_router.post("/workspaces/select", response_model=WorkspaceResponse)
async def select_workspace(request: WorkspaceSelectRequest, session: AsyncSession = Depends(get_db)) -> WorkspaceResponse:
    workspace = await ensure_workspace(session, request.workspace_id)
    return _to_workspace_response(workspace)


@api_router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    workspace_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    await ensure_workspace(session, workspace_id)
    extension = ensure_supported_extension(file.filename or "", settings.supported_extensions)

    logger.info("Upload started: workspace_id=%s filename=%s", workspace_id, file.filename)

    payload = await file.read()
    try:
        _validate_upload_size(len(payload))
    except HTTPException:
        logger.warning(
            "Upload rejected: workspace_id=%s filename=%s size_bytes=%s max_bytes=%s",
            workspace_id,
            file.filename,
            len(payload),
            settings.max_upload_size_mb * 1024 * 1024,
        )
        raise

    document_id = uuid.uuid4()
    stored_path = _store_document_file(workspace_id, document_id, extension, payload)

    document = Document(
        id=document_id,
        workspace_id=workspace_id,
        filename=file.filename or stored_path.name,
        file_type=extension,
        file_size=len(payload),
        storage_path=str(stored_path),
        processing_status=DocumentStatus.PROCESSING,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    logger.info(
        "Upload saved: document_id=%s workspace_id=%s filename=%s size_bytes=%s",
        document.id,
        workspace_id,
        document.filename,
        len(payload),
    )

    background_tasks.add_task(
        process_document,
        SessionLocal,
        workspace_id,
        document.id,
        payload,
        extension,
        embedder,
        settings.chunk_size,
        settings.chunk_overlap,
    )

    logger.info("Processing scheduled: document_id=%s workspace_id=%s", document.id, workspace_id)
    return _to_document_response(document)


@api_router.put("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    background_tasks: BackgroundTasks,
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    document = await ensure_document_in_workspace(session, workspace_id, document_id)
    extension = ensure_supported_extension(file.filename or "", settings.supported_extensions)

    logger.info("Update started: document_id=%s workspace_id=%s filename=%s", document_id, workspace_id, file.filename)

    payload = await file.read()
    _validate_upload_size(len(payload))

    old_path = Path(document.storage_path)
    stored_path = _store_document_file(workspace_id, document.id, extension, payload)
    if old_path != stored_path and old_path.exists():
        old_path.unlink()

    document.filename = file.filename or stored_path.name
    document.file_type = extension
    document.file_size = len(payload)
    document.storage_path = str(stored_path)
    document.processing_status = DocumentStatus.PROCESSING
    document.error_message = None
    document.total_pages = 0
    await session.commit()
    await session.refresh(document)

    background_tasks.add_task(
        process_document,
        SessionLocal,
        workspace_id,
        document.id,
        payload,
        extension,
        embedder,
        settings.chunk_size,
        settings.chunk_overlap,
    )

    logger.info("Processing scheduled after update: document_id=%s workspace_id=%s", document.id, workspace_id)
    return _to_document_response(document)


@api_router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    await ensure_workspace(session, workspace_id)
    documents = (
        await session.scalars(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(desc(Document.created_at))
        )
    ).all()
    return [_to_document_response(document) for document in documents]


@api_router.get("/documents/{document_id}/status", response_model=DocumentResponse)
async def get_document_status(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    document = await ensure_document_in_workspace(session, workspace_id, document_id)
    return _to_document_response(document)


@api_router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    document = await ensure_document_in_workspace(session, workspace_id, document_id)
    path = Path(document.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    return FileResponse(path=path, filename=document.filename)


@api_router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
) -> None:
    document = await ensure_document_in_workspace(session, workspace_id, document_id)
    path = Path(document.storage_path)

    await session.delete(document)
    await session.commit()

    if path.exists():
        path.unlink()


async def _execute_search(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    query_text: str,
    top_k: int,
) -> list[SearchResultItem]:
    query_embedding = embedder.embed(query_text)
    distance = Chunk.embedding.cosine_distance(query_embedding)
    candidate_limit = max(top_k * 5, top_k)
    query: Select = (
        select(Chunk, Document.filename, (1 - distance).label("similarity"))
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.workspace_id == workspace_id, Document.workspace_id == workspace_id)
        .order_by(distance)
        .limit(candidate_limit)
    )
    rows = (await session.execute(query)).all()

    matched_results: list[SearchResultItem] = []
    fallback_results: list[SearchResultItem] = []
    for chunk, filename, similarity in rows:
        fragment, has_match = _build_search_fragment(chunk.content, query_text)
        result_item = SearchResultItem(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_name=filename,
            page_number=chunk.page_number,
            text=fragment,
            similarity_score=float(similarity),
            document_link=f"/api/documents/{chunk.document_id}/download?workspace_id={workspace_id}",
        )
        if has_match:
            matched_results.append(result_item)
        else:
            fallback_results.append(result_item)

    if matched_results:
        return matched_results[:top_k]

    return fallback_results[:top_k]


@api_router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, session: AsyncSession = Depends(get_db)) -> SearchResponse:
    await ensure_workspace(session, request.workspace_id)

    try:
        top_k = min(request.top_k, settings.max_top_k)
        results = await _execute_search(session, request.workspace_id, request.query_text, top_k)

        session.add(
            SearchHistory(
                workspace_id=request.workspace_id,
                query_text=request.query_text,
                results_count=len(results),
                success=True,
            )
        )
        await session.commit()
        return SearchResponse(query_text=request.query_text, workspace_id=request.workspace_id, results=results)
    except Exception as exc:
        session.add(
            SearchHistory(
                workspace_id=request.workspace_id,
                query_text=request.query_text,
                results_count=0,
                success=False,
                error_message=str(exc)[:2000],
            )
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка выполнения поиска") from exc


@api_router.get("/search/history", response_model=list[SearchHistoryItem])
async def get_search_history(
    workspace_id: uuid.UUID = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[SearchHistoryItem]:
    await ensure_workspace(session, workspace_id)
    history_rows = (
        await session.scalars(
            select(SearchHistory)
            .where(SearchHistory.workspace_id == workspace_id)
            .order_by(desc(SearchHistory.executed_at))
            .limit(limit)
        )
    ).all()

    return [
        SearchHistoryItem(
            id=item.id,
            workspace_id=item.workspace_id,
            query_text=item.query_text,
            results_count=item.results_count,
            success=item.success,
            error_message=item.error_message,
            executed_at=item.executed_at,
        )
        for item in history_rows
    ]


@api_router.post("/search/history/{history_id}/rerun", response_model=SearchResponse)
async def rerun_search(history_id: uuid.UUID, request: RerunSearchRequest, session: AsyncSession = Depends(get_db)) -> SearchResponse:
    history_item = await session.scalar(
        select(SearchHistory).where(
            SearchHistory.id == history_id,
            SearchHistory.workspace_id == request.workspace_id,
        )
    )
    if history_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись истории не найдена")

    results = await _execute_search(session, request.workspace_id, history_item.query_text, min(request.top_k, settings.max_top_k))
    session.add(
        SearchHistory(
            workspace_id=request.workspace_id,
            query_text=history_item.query_text,
            results_count=len(results),
            success=True,
        )
    )
    await session.commit()

    return SearchResponse(query_text=history_item.query_text, workspace_id=request.workspace_id, results=results)
