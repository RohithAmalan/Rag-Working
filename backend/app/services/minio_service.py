from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from app.utils.config import settings

logger = logging.getLogger(__name__)


class MinioService:
    """Optional MinIO object storage service.

    If MinIO is not configured, this service remains disabled and callers
    can keep using local file paths.
    """

    def __init__(self) -> None:
        self.enabled = bool(settings.minio_enabled)
        self.bucket = settings.minio_bucket
        self._client = None

        if not self.enabled:
            return

        if (
            not settings.minio_endpoint
            or not settings.minio_access_key
            or not settings.minio_secret_key
        ):
            logger.warning(
                "MinIO is enabled but credentials are incomplete. Falling back to local storage."
            )
            self.enabled = False
            return

        self._init_client()

    def _init_client(self) -> bool:
        """Initialize MinIO client and ensure bucket exists.

        This supports lazy reconnection when MinIO starts after backend boot.
        """
        if not self.enabled:
            return False

        try:
            from minio import Minio

            self._client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )

            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
                logger.info("Created MinIO bucket: %s", self.bucket)

            logger.info("MinIO storage is enabled (bucket=%s)", self.bucket)
            return True
        except Exception as exc:
            logger.warning(
                "MinIO initialization failed (%s). Falling back to local storage.", exc
            )
            self._client = None
            return False

    def upload_file(self, local_path: Path, original_name: str) -> dict[str, str]:
        """Upload a local file to MinIO and return storage metadata."""
        if not self.enabled:
            return {
                "storage_backend": "local",
                "storage_path": str(local_path),
                "storage_bucket": "",
                "storage_object": "",
                "storage_url": "",
            }

        # If MinIO was unavailable during app startup, try to reconnect now.
        if self._client is None and not self._init_client():
            return {
                "storage_backend": "local",
                "storage_path": str(local_path),
                "storage_bucket": "",
                "storage_object": "",
                "storage_url": "",
            }

        object_name = f"{uuid4().hex}_{Path(original_name).name}"
        try:
            self._client.fput_object(self.bucket, object_name, str(local_path))
        except Exception as exc:
            logger.warning(
                "MinIO upload failed (%s). Falling back to local storage metadata.", exc
            )
            return {
                "storage_backend": "local",
                "storage_path": str(local_path),
                "storage_bucket": "",
                "storage_object": "",
                "storage_url": "",
            }

        return {
            "storage_backend": "minio",
            "storage_path": f"s3://{self.bucket}/{object_name}",
            "storage_bucket": self.bucket,
            "storage_object": object_name,
            "storage_url": f"{settings.minio_endpoint}/{self.bucket}/{object_name}",
        }

    def delete_object(self, object_name: str) -> bool:
        """Delete an object from MinIO bucket."""
        if not self.enabled:
            return False

        if self._client is None and not self._init_client():
            return False

        try:
            self._client.remove_object(self.bucket, object_name)
            return True
        except Exception as exc:
            logger.warning("MinIO delete failed for %s (%s)", object_name, exc)
            return False

    def download_file(self, object_name: str, local_path: Path) -> bool:
        """Download a file from MinIO to a local path.

        Args:
            object_name: Name of the object in MinIO bucket
            local_path: Local path where to save the file

        Returns:
            True if download succeeded, False otherwise
        """
        if not self.enabled:
            return False

        if self._client is None and not self._init_client():
            return False

        try:
            self._client.fget_object(self.bucket, object_name, str(local_path))
            return True
        except Exception as exc:
            logger.warning("MinIO download failed for %s (%s)", object_name, exc)
            return False
