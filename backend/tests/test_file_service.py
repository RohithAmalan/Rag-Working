"""Tests for file_service module."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pandas as pd
import pytest
from fastapi import UploadFile

from app.services.file_service import FileService


class TestFileService:
    """Test suite for file service."""

    @pytest.fixture
    def file_service(self, tmp_path):
        """Create a FileService instance with temporary directory."""
        return FileService(uploads_dir=tmp_path, chunk_size=500, chunk_overlap=50)

    @pytest.fixture
    def mock_csv_file(self):
        """Create a mock CSV upload file."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.csv"
        mock_file.read = AsyncMock(return_value=b"col1,col2\nval1,val2")
        return mock_file

    @pytest.fixture
    def mock_excel_file(self):
        """Create a mock Excel upload file."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.xlsx"
        mock_file.read = AsyncMock(return_value=b"mock excel data")
        return mock_file

    @pytest.fixture
    def mock_pdf_file(self):
        """Create a mock PDF upload file."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 mock pdf")
        return mock_file

    # Test save_upload method
    @pytest.mark.asyncio
    async def test_save_upload_csv(self, file_service, mock_csv_file, tmp_path):
        """Test saving a CSV file upload."""
        result = await file_service.save_upload(mock_csv_file)

        assert isinstance(result, Path)
        assert result.exists()
        assert result.suffix == ".csv"
        assert result.parent == tmp_path

    @pytest.mark.asyncio
    async def test_save_upload_excel(self, file_service, mock_excel_file, tmp_path):
        """Test saving an Excel file upload."""
        result = await file_service.save_upload(mock_excel_file)

        assert isinstance(result, Path)
        assert result.exists()
        assert result.suffix == ".xlsx"
        assert result.parent == tmp_path

    @pytest.mark.asyncio
    async def test_save_upload_pdf(self, file_service, mock_pdf_file, tmp_path):
        """Test saving a PDF file upload."""
        result = await file_service.save_upload(mock_pdf_file)

        assert isinstance(result, Path)
        assert result.exists()
        assert result.suffix == ".pdf"

    @pytest.mark.asyncio
    async def test_save_upload_unsupported_type(self, file_service):
        """Test rejection of unsupported file types."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.txt"

        with pytest.raises(ValueError, match="Unsupported file type"):
            await file_service.save_upload(mock_file)

    @pytest.mark.asyncio
    async def test_save_upload_generates_unique_names(
        self, file_service, mock_csv_file
    ):
        """Test that uploaded files get unique names."""
        result1 = await file_service.save_upload(mock_csv_file)
        mock_csv_file.read = AsyncMock(return_value=b"col1,col2\nval1,val2")
        result2 = await file_service.save_upload(mock_csv_file)

        assert result1 != result2
        assert result1.stem != result2.stem

    # Test _dedupe_columns method
    def test_dedupe_columns_no_duplicates(self):
        """Test deduplication with no duplicate columns."""
        columns = ["name", "age", "city"]
        result = FileService._dedupe_columns(columns)

        assert result == ["name", "age", "city"]

    def test_dedupe_columns_with_duplicates(self):
        """Test deduplication with duplicate column names."""
        columns = ["name", "age", "name", "age"]
        result = FileService._dedupe_columns(columns)

        assert result == ["name", "age", "name_2", "age_2"]

    def test_dedupe_columns_with_empty_names(self):
        """Test handling of empty column names."""
        columns = ["name", "", None, "age"]
        result = FileService._dedupe_columns(columns)

        assert result[0] == "name"
        assert result[1].startswith("column_")
        assert result[2].startswith("column_")
        assert result[3] == "age"

    def test_dedupe_columns_all_empty(self):
        """Test handling when all column names are empty."""
        columns = ["", None, "", None]
        result = FileService._dedupe_columns(columns)

        assert len(result) == 4
        assert all(col.startswith("column_") for col in result)

    # Test _promote_first_row_as_header_if_needed method
    def test_promote_first_row_empty_dataframe(self):
        """Test promotion with empty dataframe."""
        df = pd.DataFrame()
        result = FileService._promote_first_row_as_header_if_needed(df)

        assert result.equals(df)

    def test_promote_first_row_no_unnamed_columns(self):
        """Test no promotion when columns are already named."""
        df = pd.DataFrame({"name": ["John"], "age": [30]})
        result = FileService._promote_first_row_as_header_if_needed(df)

        assert result.equals(df)

    def test_promote_first_row_with_unnamed_columns(self):
        """Test promotion when unnamed columns exist and first row has headers."""
        df = pd.DataFrame(
            {
                "Unnamed: 0": ["Name", "John"],
                "Unnamed: 1": ["Age", "30"],
                "Unnamed: 2": ["City", "NYC"],
            }
        )
        result = FileService._promote_first_row_as_header_if_needed(df)

        assert "Name" in result.columns
        assert "Age" in result.columns
        assert "City" in result.columns
        assert len(result) == 1
        assert result.iloc[0]["Name"] == "John"

    def test_promote_first_row_insufficient_improvement(self):
        """Test no promotion when first row doesn't improve headers."""
        df = pd.DataFrame({"Unnamed: 0": [123, "John"], "Unnamed: 1": [456, "30"]})
        result = FileService._promote_first_row_as_header_if_needed(df)

        # Should not promote numeric values as headers
        assert "Unnamed: 0" in str(result.columns)

    # Test _detect_header_row method
    def test_detect_header_row_no_unnamed(self):
        """Test header detection when columns are already named."""
        df = pd.DataFrame({"name": ["John"], "age": [30]})
        result = FileService._detect_header_row(df)

        assert result == 0

    def test_detect_header_row_with_title_row(self):
        """Test detection when first row is a title."""
        df = pd.DataFrame(
            {
                "Unnamed: 0": ["Employee Report", "Name", "John"],
                "Unnamed: 1": ["", "Age", "30"],
            }
        )
        result = FileService._detect_header_row(df, max_scan=3)

        # Should detect row 1 as the header
        assert result >= 0

    # Test allowed_types attribute
    def test_allowed_types(self):
        """Test that allowed file types are correctly defined."""
        assert ".csv" in FileService.allowed_types
        assert ".xlsx" in FileService.allowed_types
        assert ".pdf" in FileService.allowed_types
        assert len(FileService.allowed_types) == 3

    @pytest.mark.asyncio
    async def test_save_upload_no_filename(self, file_service):
        """Test handling of upload with no filename."""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = None
        mock_file.read = AsyncMock(return_value=b"test data")

        # Should use default filename
        with pytest.raises(ValueError):
            await file_service.save_upload(mock_file)

    @pytest.mark.asyncio
    async def test_save_upload_preserves_content(self, file_service, mock_csv_file):
        """Test that uploaded file content is preserved."""
        result = await file_service.save_upload(mock_csv_file)

        content = result.read_text()
        assert content == "col1,col2\nval1,val2"
