import asyncio
import uuid
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from rag_system.models import Chunk, Document, DocumentStatus
from rag_system.services.chunking import chunk_pages
from rag_system.services.document_parser import parse_document
from rag_system.services.embedding import HashEmbeddingService


logger = logging.getLogger(__name__)


def _parse_chunk_and_embed(
    source_bytes: bytes,
    file_extension: str,
    embedder: HashEmbeddingService,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list, list, list[list[float]]]:
    pages = parse_document(file_extension, source_bytes)
    chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    vectors = embedder.embed_batch([chunk.content for chunk in chunks])
    return pages, chunks, vectors


async def process_document(
    session_factory: async_sessionmaker,
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    source_bytes: bytes,
    file_extension: str,
    embedder: HashEmbeddingService,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    logger.info("Processing started: document_id=%s workspace_id=%s", document_id, workspace_id)

    async with session_factory() as session:
        document = await session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
            )
        )
        if document is None:
            logger.warning("Processing aborted: document not found document_id=%s workspace_id=%s", document_id, workspace_id)
            return

        document.processing_status = DocumentStatus.PROCESSING
        document.error_message = None
        await session.commit()

    try:
        pages, chunks, vectors = await asyncio.to_thread(
            _parse_chunk_and_embed,
            source_bytes,
            file_extension,
            embedder,
            chunk_size,
            chunk_overlap,
        )

        async with session_factory() as session:
            document = await session.scalar(
                select(Document).where(
                    Document.id == document_id,
                    Document.workspace_id == workspace_id,
                )
            )
            if document is None:
                logger.warning(
                    "Processing aborted before save: document not found document_id=%s workspace_id=%s",
                    document_id,
                    workspace_id,
                )
                return

            await session.execute(delete(Chunk).where(Chunk.document_id == document.id))

            for item, vector in zip(chunks, vectors, strict=True):
                session.add(
                    Chunk(
                        workspace_id=workspace_id,
                        document_id=document.id,
                        page_number=item.page_number,
                        chunk_index=item.chunk_index,
                        content=item.content,
                        embedding=vector,
                    )
                )

            document.total_pages = len(pages)
            document.processing_status = DocumentStatus.READY
            document.error_message = None
            await session.commit()
            logger.info(
                "Processing finished: document_id=%s workspace_id=%s pages=%s chunks=%s",
                document_id,
                workspace_id,
                len(pages),
                len(chunks),
            )
    except Exception as exc:
        logger.exception("Processing failed: document_id=%s workspace_id=%s", document_id, workspace_id)
        async with session_factory() as session:
            document = await session.scalar(
                select(Document).where(
                    Document.id == document_id,
                    Document.workspace_id == workspace_id,
                )
            )
            if document is None:
                return

            document.processing_status = DocumentStatus.FAILED
            document.error_message = str(exc)[:2000]
            await session.commit()
