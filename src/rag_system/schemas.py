import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from rag_system.models import DocumentStatus


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class WorkspaceSelectRequest(BaseModel):
    workspace_id: uuid.UUID


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


class DocumentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    processing_status: DocumentStatus
    error_message: str | None
    total_pages: int
    created_at: datetime


class SearchRequest(BaseModel):
    workspace_id: uuid.UUID
    query_text: str = Field(min_length=1, max_length=4_000)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    text: str
    similarity_score: float
    document_link: str


class SearchResponse(BaseModel):
    query_text: str
    workspace_id: uuid.UUID
    results: list[SearchResultItem]


class SearchHistoryItem(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    query_text: str
    results_count: int
    success: bool
    error_message: str | None
    executed_at: datetime


class RerunSearchRequest(BaseModel):
    workspace_id: uuid.UUID
    top_k: int = Field(default=5, ge=1, le=20)
