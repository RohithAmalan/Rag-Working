from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.utils.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/storage-status")
async def storage_status():
    """Report where uploaded data is currently being stored."""
    from app.main import app

    backend = getattr(app.state, "storage_backend", "unknown")
    return {
        "backend": backend,
        "database_name": settings.database_name,
        "collections": {
            "documents": settings.documents_collection,
            "chunks": settings.chunks_collection,
        },
        "local_paths": {
            "uploads_dir": str(settings.uploads_dir),
            "chunk_cache": str(settings.cache_file),
            "vector_dir": str(settings.vector_dir),
        },
    }
