"""Tests for mongo_vector_service module."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.services.mongo_vector_service import (MongoVectorService,
                                               _build_file_hint_filter,
                                               _extract_exact_terms,
                                               _matches_file_hints)
from bson import ObjectId


class TestExtractExactTerms:
    """Test suite for term extraction functions."""

    def test_extract_ids_alphanumeric(self):
        """Test extraction of alphanumeric IDs."""
        query = "Find order ABC123 and REG100138"
        result = _extract_exact_terms(query)

        assert "ABC123" in result["ids"]
        assert "REG100138" in result["ids"]

    def test_extract_ids_hyphenated(self):
        """Test extraction of hyphenated IDs."""
        query = "Show me ORD-10028 and C-5076"
        result = _extract_exact_terms(query)

        assert "ORD-10028" in result["ids"] or "10028" in str(result["ids"])
        assert "C-5076" in result["ids"] or "5076" in str(result["ids"])

    def test_extract_phone_numbers(self):
        """Test extraction of phone numbers."""
        query = "Call +1-555-123-4567 or (555) 987-6543"
        result = _extract_exact_terms(query)

        assert len(result["phones"]) > 0

    def test_extract_emails(self):
        """Test extraction of email addresses."""
        query = "Contact john.doe@example.com or support@company.org"
        result = _extract_exact_terms(query)

        assert "john.doe@example.com" in result["emails"]
        assert "support@company.org" in result["emails"]

    def test_extract_full_names(self):
        """Test extraction of full names."""
        query = "Find records for Donna Harris and John Smith"
        result = _extract_exact_terms(query)

        assert "Donna Harris" in result["full_names"]
        assert "John Smith" in result["full_names"]

    def test_extract_capitalized_names(self):
        """Test extraction of single capitalized names."""
        query = "Show data for Alice and Bob"
        result = _extract_exact_terms(query)

        assert "Alice" in result["names"]
        assert "Bob" in result["names"]

    def test_extract_file_hints(self):
        """Test extraction of file name hints."""
        query = "Check the people-100.csv file and product-sales-region data"
        result = _extract_exact_terms(query)

        assert any("people" in hint.lower() for hint in result["file_hints"])

    def test_extract_no_duplicates(self):
        """Test that duplicates are removed."""
        query = "ABC123 and ABC123 again"
        result = _extract_exact_terms(query)

        # Count occurrences of ABC123
        count = sum(1 for id in result["ids"] if "ABC123" in id)
        assert count == 1

    def test_extract_empty_query(self):
        """Test handling of empty query."""
        result = _extract_exact_terms("")

        assert result["ids"] == []
        assert result["phones"] == []
        assert result["emails"] == []


class TestFileHintFunctions:
    """Test suite for file hint filtering functions."""

    def test_build_file_hint_filter_empty(self):
        """Test building filter with no hints."""
        result = _build_file_hint_filter([])
        assert result is None

    def test_build_file_hint_filter_single_hint(self):
        """Test building filter with single hint."""
        result = _build_file_hint_filter(["customers"])

        assert result is not None
        assert "$or" in result

    def test_build_file_hint_filter_multiple_hints(self):
        """Test building filter with multiple hints."""
        result = _build_file_hint_filter(["customers", "people"])

        assert result is not None
        assert "$or" in result
        assert len(result["$or"]) > 0

    def test_matches_file_hints_exact_match(self):
        """Test exact file name matching."""
        metadata = {"file_name": "customers-100.csv"}
        file_hints = ["customers"]

        assert _matches_file_hints(metadata, file_hints) is True

    def test_matches_file_hints_normalized_match(self):
        """Test normalized file name matching."""
        metadata = {"file_name": "product_sales_region.xlsx"}
        file_hints = ["product-sales-region"]

        assert _matches_file_hints(metadata, file_hints) is True

    def test_matches_file_hints_no_match(self):
        """Test file name not matching."""
        metadata = {"file_name": "orders.csv"}
        file_hints = ["customers"]

        assert _matches_file_hints(metadata, file_hints) is False

    def test_matches_file_hints_empty_hints(self):
        """Test that empty hints match everything."""
        metadata = {"file_name": "any-file.csv"}

        assert _matches_file_hints(metadata, []) is True


class TestMongoVectorService:
    """Test suite for MongoVectorService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.chunks = MagicMock()
        db.documents = MagicMock()

        from app.utils.config import settings

        # Mock dictionary access like db["documents"] and db["chunks"]
        collections_map = {
            "documents": db.documents,
            "chunks": db.chunks,
            settings.documents_collection: db.documents,
            settings.chunks_collection: db.chunks,
        }
        db.__getitem__.side_effect = lambda key: collections_map.get(key, MagicMock())
        return db

    @pytest.fixture
    def vector_service(self, mock_db):
        """Create a MongoVectorService instance."""
        return MongoVectorService(mock_db)

    @pytest.mark.asyncio
    async def test_store_document_chunks_basic(self, vector_service, mock_db):
        """Test storing document chunks."""
        # Mock the database operations
        mock_db.documents.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )
        mock_db.chunks.insert_many = AsyncMock(
            return_value=MagicMock(inserted_ids=[ObjectId(), ObjectId()])
        )

        with patch(
            "app.services.mongo_vector_service.generate_batch_embeddings"
        ) as mock_embed:
            mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

            result = await vector_service.store_document_chunks(
                filename="test.csv",
                file_type="csv",
                path="/test/path",
                chunk_texts=["chunk1", "chunk2"],
                chunk_metadata_list=[{}, {}],
            )

            assert result["chunks_stored"] == 2
            assert "document_id" in result
            mock_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_document_chunks_empty(self, vector_service):
        """Test storing with empty chunks list."""
        with pytest.raises(Exception):
            await vector_service.store_document_chunks(
                filename="test.csv",
                file_type="csv",
                path="/test/path",
                chunk_texts=[],
                chunk_metadata_list=[],
            )

    @pytest.mark.asyncio
    async def test_hybrid_search(self, vector_service, mock_db):
        """Test hybrid search functionality."""
        # Mock the vector search results
        mock_db.chunks.aggregate = MagicMock(
            return_value=MagicMock(
                to_list=AsyncMock(
                    return_value=[
                        {
                            "_id": ObjectId(),
                            "chunk_text": "test chunk",
                            "source": "test.csv",
                            "document_id": str(ObjectId()),
                            "chunk_index": 0,
                            "similarity_score": 0.9,
                            "metadata": {"file_name": "test.csv"},
                        }
                    ]
                )
            )
        )

        with patch(
            "app.services.embedding_service.generate_single_embedding"
        ) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            results = await vector_service.search_chunks(
                query_text="test query", top_k=5
            )

            assert len(results) > 0
            mock_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_documents(self, vector_service, mock_db):
        """Test retrieving all documents."""
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "filename": "test.csv",
                    "uploaded_at": "2024-01-01",
                }
            ]
        )
        mock_db.documents.find.return_value = mock_cursor

        results = await vector_service.get_all_documents()

        assert len(results) > 0
        assert isinstance(results[0]["_id"], str)

    @pytest.mark.asyncio
    async def test_delete_document(self, vector_service, mock_db):
        """Test document deletion."""
        doc_id = str(ObjectId())

        mock_db.documents.find_one = AsyncMock(return_value={"_id": ObjectId(doc_id)})
        mock_db.documents.delete_one = AsyncMock(
            return_value=MagicMock(deleted_count=1)
        )
        mock_db.chunks.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))

        result = await vector_service.delete_document_and_chunks(doc_id)

        assert result == 5

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, vector_service, mock_db):
        """Test deletion of non-existent document."""
        doc_id = str(ObjectId())

        mock_db.documents.find_one = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await vector_service.delete_document_and_chunks(doc_id)

    @pytest.mark.asyncio
    async def test_search_with_file_filter(self, vector_service, mock_db):
        """Test search with file filtering."""
        mock_db.chunks.aggregate = MagicMock(
            return_value=MagicMock(
                to_list=AsyncMock(
                    return_value=[
                        {
                            "_id": ObjectId(),
                            "chunk_text": "test chunk",
                            "source": "customers-100.csv",
                            "document_id": str(ObjectId()),
                            "chunk_index": 0,
                            "similarity_score": 0.9,
                            "metadata": {"file_name": "customers-100.csv"},
                        }
                    ]
                )
            )
        )

        with patch(
            "app.services.embedding_service.generate_single_embedding"
        ) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            # Search with file hint
            await vector_service.search_chunks(
                query_text="find in customers file", top_k=5
            )

            # Should have called embedding generation
            mock_embed.assert_called()
