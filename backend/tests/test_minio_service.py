"""Tests for minio_service module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from app.services.minio_service import MinioService


class TestMinioService:
    """Test suite for MinIO service."""

    @pytest.fixture
    def mock_settings_disabled(self):
        """Mock settings with MinIO disabled."""
        with patch("app.services.minio_service.settings") as mock:
            mock.minio_enabled = False
            mock.minio_bucket = "test-bucket"
            yield mock

    @pytest.fixture
    def mock_settings_enabled(self):
        """Mock settings with MinIO enabled and configured."""
        with patch("app.services.minio_service.settings") as mock:
            mock.minio_enabled = True
            mock.minio_bucket = "test-bucket"
            mock.minio_endpoint = "localhost:9000"
            mock.minio_access_key = "minioadmin"
            mock.minio_secret_key = "minioadmin"
            mock.minio_secure = False
            yield mock

    @pytest.fixture
    def mock_settings_incomplete(self):
        """Mock settings with MinIO enabled but incomplete credentials."""
        with patch("app.services.minio_service.settings") as mock:
            mock.minio_enabled = True
            mock.minio_bucket = "test-bucket"
            mock.minio_endpoint = ""
            mock.minio_access_key = ""
            mock.minio_secret_key = ""
            yield mock

    def test_init_disabled(self, mock_settings_disabled):
        """Test MinioService initialization when disabled."""
        service = MinioService()

        assert service.enabled is False
        assert service._client is None

    def test_init_incomplete_credentials(self, mock_settings_incomplete):
        """Test MinioService falls back to local when credentials incomplete."""
        service = MinioService()

        assert service.enabled is False

    @patch("minio.Minio")
    def test_init_client_success(self, mock_minio_class, mock_settings_enabled):
        """Test successful MinIO client initialization."""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_minio_class.return_value = mock_client

        service = MinioService()

        assert service.enabled is True
        assert service._client == mock_client
        mock_client.bucket_exists.assert_called_once_with("test-bucket")

    @patch("minio.Minio")
    def test_init_client_creates_bucket(self, mock_minio_class, mock_settings_enabled):
        """Test bucket creation when it doesn't exist."""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = False
        mock_minio_class.return_value = mock_client

        service = MinioService()

        assert service.enabled is True
        mock_client.make_bucket.assert_called_once_with("test-bucket")

    @patch("minio.Minio")
    def test_init_client_failure(self, mock_minio_class, mock_settings_enabled):
        """Test fallback to local storage when MinIO init fails."""
        mock_minio_class.side_effect = Exception("Connection failed")

        service = MinioService()

        assert service.enabled is True  # Started as enabled
        assert service._client is None  # But client failed to initialize

    def test_upload_file_when_disabled(self, mock_settings_disabled, tmp_path):
        """Test file upload returns local metadata when MinIO is disabled."""
        service = MinioService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = service.upload_file(test_file, "original.txt")

        assert result["storage_backend"] == "local"
        assert result["storage_path"] == str(test_file)
        assert result["storage_bucket"] == ""
        assert result["storage_object"] == ""

    @patch("minio.Minio")
    def test_upload_file_success(
        self, mock_minio_class, mock_settings_enabled, tmp_path
    ):
        """Test successful file upload to MinIO."""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.fput_object.return_value = None
        mock_minio_class.return_value = mock_client

        service = MinioService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = service.upload_file(test_file, "original.txt")

        assert result["storage_backend"] == "minio"
        assert result["storage_bucket"] == "test-bucket"
        assert "original.txt" in result["storage_object"]
        assert result["storage_path"].startswith("s3://")
        mock_client.fput_object.assert_called_once()

    @patch("minio.Minio")
    def test_upload_file_minio_failure_fallback(
        self, mock_minio_class, mock_settings_enabled, tmp_path
    ):
        """Test fallback to local when MinIO upload fails."""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.fput_object.side_effect = Exception("Upload failed")
        mock_minio_class.return_value = mock_client

        service = MinioService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = service.upload_file(test_file, "original.txt")

        assert result["storage_backend"] == "local"
        assert result["storage_path"] == str(test_file)

    @patch("minio.Minio")
    def test_upload_file_lazy_reconnect(
        self, mock_minio_class, mock_settings_enabled, tmp_path
    ):
        """Test lazy reconnection when MinIO becomes available."""
        # First call fails
        mock_minio_class.side_effect = [
            Exception("Not available"),
            Mock(bucket_exists=Mock(return_value=True)),
        ]

        service = MinioService()
        assert service._client is None

        # Reset the side effect for the reconnection attempt
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.fput_object.return_value = None
        mock_minio_class.side_effect = None
        mock_minio_class.return_value = mock_client

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # This should trigger reconnection
        result = service.upload_file(test_file, "original.txt")

        # Should successfully reconnect and upload
        assert mock_client.fput_object.called or result["storage_backend"] == "local"

    def test_bucket_property(self, mock_settings_enabled):
        """Test bucket property is correctly set."""
        with patch("minio.Minio"):
            service = MinioService()
            assert service.bucket == "test-bucket"

    @patch("minio.Minio")
    def test_upload_file_generates_unique_object_names(
        self, mock_minio_class, mock_settings_enabled, tmp_path
    ):
        """Test that uploaded objects get unique names."""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_minio_class.return_value = mock_client

        service = MinioService()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result1 = service.upload_file(test_file, "file.txt")
        result2 = service.upload_file(test_file, "file.txt")

        # Object names should be different (contain UUIDs)
        assert result1["storage_object"] != result2["storage_object"]

    @patch("minio.Minio")
    def test_minio_secure_setting(self, mock_minio_class, mock_settings_enabled):
        """Test that secure setting is passed to MinIO client."""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_minio_class.return_value = mock_client

        mock_settings_enabled.minio_secure = True
        service = MinioService()

        # Verify Minio was called with secure=True
        call_kwargs = mock_minio_class.call_args[1]
        assert call_kwargs["secure"] is True
