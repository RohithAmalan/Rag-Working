from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Excel-First RAG Assistant"
    environment: str = "development"
    api_prefix: str = ""

    # LLM Configuration
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    openai_api_key: str = ""

    # File Configuration
    uploads_dir: Path = Field(default=Path("app/uploads/files"))
    vector_dir: Path = Field(default=Path("app/vectorstore/data"))
    cache_file: Path = Field(default=Path("app/vectorstore/chunk_cache.json"))

    # Chunking Configuration
    chunk_size: int = Field(default=900, validation_alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=120, validation_alias="CHUNK_OVERLAP")

    # MongoDB Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        validation_alias="MONGODB_URI",
    )
    database_name: str = Field(default="rag_db", validation_alias="DATABASE_NAME")
    documents_collection: str = Field(
        default="documents", validation_alias="DOCUMENTS_COLLECTION"
    )
    chunks_collection: str = Field(
        default="chunks", validation_alias="CHUNKS_COLLECTION"
    )
    allow_start_without_mongo: bool = Field(
        default=True,
        validation_alias="ALLOW_START_WITHOUT_MONGO",
    )

    # Embedding Configuration
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=384, validation_alias="EMBEDDING_DIMENSION")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
settings.vector_dir.mkdir(parents=True, exist_ok=True)
settings.cache_file.parent.mkdir(parents=True, exist_ok=True)
