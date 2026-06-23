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

    # MinIO Configuration (optional)
    minio_enabled: bool = Field(default=False, validation_alias="MINIO_ENABLED")
    minio_endpoint: str = Field(default="", validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="", validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="rag-files", validation_alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")

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

    # LangGraph Workflow Configuration
    langgraph_workflow_mode: str = Field(
        default="multi_agent",  # Options: "basic", "advanced", "multi_agent"
        validation_alias="LANGGRAPH_WORKFLOW_MODE",
    )

    # Keycloak Configuration
    keycloak_url: str = Field(default="", validation_alias="KEYCLOAK_URL")
    keycloak_realm: str = Field(default="rag-realm", validation_alias="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(default="rag-app", validation_alias="KEYCLOAK_CLIENT_ID")

    # Redis Semantic Cache Configuration
    redis_enabled: bool = Field(default=True, validation_alias="REDIS_ENABLED")
    redis_url: str = Field(default="redis://localhost:6379", validation_alias="REDIS_URL")
    cache_similarity_threshold: float = Field(
        default=0.92,
        validation_alias="CACHE_SIMILARITY_THRESHOLD",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        validation_alias="CACHE_TTL_SECONDS",
    )

    # n8n Workflow Automation
    n8n_webhook_url: str = Field(
        default="http://localhost:5678/webhook/rag-event",
        validation_alias="N8N_WEBHOOK_URL",
    )

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
