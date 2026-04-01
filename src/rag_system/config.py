from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")

    app_name: str = "Workspace RAG Search"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rag_search"
    uploads_dir: Path = Path("data") / "uploads"

    embedding_dim: int = 384
    chunk_size: int = 1200
    chunk_overlap: int = 200

    max_upload_size_mb: int = 30
    supported_extensions: tuple[str, ...] = (".pdf", ".docx", ".txt")
    default_top_k: int = 5
    max_top_k: int = Field(default=20)

    host: str = Field(default="127.0.0.1", validation_alias=AliasChoices("HOST", "RAG_HOST"))
    port: int = Field(default=8000, ge=1, le=65535, validation_alias=AliasChoices("PORT", "RAG_PORT"))
    log_level: str = Field(default="info", validation_alias=AliasChoices("LOG_LEVEL", "RAG_LOG_LEVEL"))


settings = Settings()
