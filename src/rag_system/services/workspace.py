import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_system.models import Document, Workspace


async def ensure_workspace(session: AsyncSession, workspace_id: uuid.UUID) -> Workspace:
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace не найден")
    return workspace


async def ensure_document_in_workspace(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document:
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден в текущем workspace")
    return document
