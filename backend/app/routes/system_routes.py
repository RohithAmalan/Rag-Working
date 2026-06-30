from fastapi import APIRouter, Depends, Response

from app.models.schemas import HealthResponse
from app.utils.config import settings
from app.utils.dependencies import require_admin
from app.utils.metrics import metrics_response

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/storage-status")
async def storage_status(current_user: dict = Depends(require_admin)):
    """Report where uploaded data is currently being stored. **Admin only.**"""
    from app.main import app

    backend = getattr(app.state, "storage_backend", "unknown")
    rag_service = getattr(app.state, "rag_service", None)
    minio_connected = False

    if rag_service is not None and hasattr(rag_service, "minio_service"):
        minio_service = getattr(rag_service, "minio_service")
        minio_connected = bool(
            getattr(minio_service, "enabled", False)
            and getattr(minio_service, "_client", None)
        )

    can_upload = (not settings.minio_enabled) or minio_connected
    return {
        "backend": backend,
        "can_upload": can_upload,
        "upload_mode": (
            "minio"
            if minio_connected
            else ("local" if not settings.minio_enabled else "blocked-minio-required")
        ),
        "minio": {
            "enabled": bool(settings.minio_enabled),
            "connected": minio_connected,
            "endpoint": settings.minio_endpoint,
            "bucket": settings.minio_bucket,
        },
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


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    payload, content_type = metrics_response()
    return Response(content=payload, media_type=content_type)
