from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_system.config import settings
from rag_system.models import Base


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivfflat
                ON chunks
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
                """
            )
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
