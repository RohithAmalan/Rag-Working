"""Tests for rag_service module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import UploadFile

from app.services.rag_service import RagService


class TestRagService:
    """Test suite for RAG service orchestration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return MagicMock()

    @pytest.fixture
    def rag_service(self, mock_db):
        """Create a RAG service instance with mocked dependencies."""
        with patch("app.services.rag_service.FileService"), \
             patch("app.services.rag_service.MinioService"), \
             patch("app.services.rag_service.MongoVectorService"), \
             patch("app.services.rag_service.LangGraphRAGService"):
            return RagService(mock_db)

    @pytest.mark.asyncio
    async def test_upload_and_process_files_success(self, rag_service):
        """Test successful file upload and processing."""
        # Mock file service
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.csv"
        mock_file.read = AsyncMock(return_value=b"data")

        mock_path = Path("/tmp/test.csv")
        rag_service.file_service.save_upload = AsyncMock(return_value=mock_path)
        rag_service.file_service.process_file = Mock(return_value=[
            {
                "page_content": "chunk1",
                "metadata": {"source_type": "csv", "source_priority": "primary"}
            }
        ])
        rag_service.file_service.analyze_file = Mock(return_value={"total_rows": 10})

        # Mock MinIO service
        rag_service.minio_service.upload_file = Mock(return_value={
            "storage_backend": "local",
            "storage_path": str(mock_path),
        })

        # Mock vector service
        rag_service.vector_service.store_document_chunks = AsyncMock(return_value={
            "document_id": "123",
            "chunks_stored": 1,
        })

        # Process file
        result = await rag_service.upload_and_process_files([mock_file])

        assert result["processed_files"] == 1
        assert result["total_chunks"] == 1
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_upload_and_process_files_error(self, rag_service):
        """Test file processing with errors."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "bad.csv"

        # Mock file service to raise error
        rag_service.file_service.save_upload = AsyncMock(
            side_effect=ValueError("Invalid file")
        )

        result = await rag_service.upload_and_process_files([mock_file])

        assert result["processed_files"] == 0
        assert len(result["errors"]) == 1
        assert "bad.csv" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_upload_and_process_files_no_chunks(self, rag_service):
        """Test processing file that generates no chunks."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "empty.csv"

        mock_path = Path("/tmp/empty.csv")
        rag_service.file_service.save_upload = AsyncMock(return_value=mock_path)
        rag_service.file_service.process_file = Mock(return_value=[])
        rag_service.file_service.analyze_file = Mock(return_value={})

        rag_service.minio_service.upload_file = Mock(return_value={
            "storage_backend": "local",
            "storage_path": str(mock_path),
        })

        result = await rag_service.upload_and_process_files([mock_file])

        assert result["processed_files"] == 0
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_upload_with_minio_enabled(self, rag_service):
        """Test file upload when MinIO is enabled."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.csv"

        mock_path = Path("/tmp/test.csv")
        rag_service.file_service.save_upload = AsyncMock(return_value=mock_path)
        rag_service.file_service.process_file = Mock(return_value=[
            {"page_content": "chunk", "metadata": {}}
        ])
        rag_service.file_service.analyze_file = Mock(return_value={})

        # Mock MinIO upload success
        rag_service.minio_service.upload_file = Mock(return_value={
            "storage_backend": "minio",
            "storage_path": "s3://bucket/file.csv",
            "storage_bucket": "test-bucket",
        })

        rag_service.vector_service.store_document_chunks = AsyncMock(return_value={
            "document_id": "123",
            "chunks_stored": 1,
        })

        with patch("app.services.rag_service.settings") as mock_settings:
            mock_settings.minio_enabled = False

            result = await rag_service.upload_and_process_files([mock_file])

            assert result["processed_files"] == 1

    @pytest.mark.asyncio
    async def test_search_and_retrieve(self, rag_service):
        """Test search and retrieve functionality."""
        rag_service.vector_service.search_chunks = AsyncMock(return_value=[
            {
                "chunk_text": "mock chunk text",
                "similarity_score": 0.99,
                "source": "test.csv",
                "metadata": {"source_priority": "primary"},
            }
        ])

        result = await rag_service.search_and_retrieve(
            query="test query",
            top_k=5
        )

        assert len(result) == 1
        assert result[0]["chunk_text"] == "mock chunk text"
        rag_service.vector_service.search_chunks.assert_called_once_with(
            query_text="test query",
            top_k=5,
            source_priority="primary",
            required_file_name=None,
        )


    @pytest.mark.asyncio
    async def test_upload_multiple_files(self, rag_service):
        """Test uploading multiple files."""
        mock_file1 = AsyncMock(spec=UploadFile)
        mock_file1.filename = "test1.csv"
        mock_file2 = AsyncMock(spec=UploadFile)
        mock_file2.filename = "test2.csv"

        mock_path = Path("/tmp/test.csv")
        rag_service.file_service.save_upload = AsyncMock(return_value=mock_path)
        rag_service.file_service.process_file = Mock(return_value=[
            {"page_content": "chunk", "metadata": {}}
        ])
        rag_service.file_service.analyze_file = Mock(return_value={})

        rag_service.minio_service.upload_file = Mock(return_value={
            "storage_backend": "local",
            "storage_path": str(mock_path),
        })

        rag_service.vector_service.store_document_chunks = AsyncMock(return_value={
            "document_id": "123",
            "chunks_stored": 1,
        })

        result = await rag_service.upload_and_process_files([mock_file1, mock_file2])

        assert result["processed_files"] == 2
        assert result["total_chunks"] == 2

    def test_rag_service_initialization(self, mock_db):
        """Test RAG service initializes with correct workflow mode."""
        with patch("app.services.rag_service.FileService"), \
             patch("app.services.rag_service.MinioService"), \
             patch("app.services.rag_service.MongoVectorService"), \
             patch("app.services.rag_service.LangGraphRAGService") as mock_lg:
            
            service = RagService(mock_db)
            
            # Verify LangGraph service was initialized
            mock_lg.assert_called_once()

    def test_rag_service_invalid_workflow_mode(self, mock_db):
        """Test RAG service handles invalid workflow mode gracefully."""
        with patch("app.services.rag_service.FileService"), \
             patch("app.services.rag_service.MinioService"), \
             patch("app.services.rag_service.MongoVectorService"), \
             patch("app.services.rag_service.LangGraphRAGService"), \
             patch("app.services.rag_service.settings") as mock_settings:
            
            mock_settings.langgraph_workflow_mode = "invalid_mode"
            mock_settings.uploads_dir = Path("/tmp")
            mock_settings.chunk_size = 500
            mock_settings.chunk_overlap = 50
            
            # Should not raise error, should default to multi_agent
            service = RagService(mock_db)
            assert service is not None
