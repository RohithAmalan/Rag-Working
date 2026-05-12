"""RAG service orchestrating the complete pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.rag.chunking import chunk_pdf_texts, dataframe_to_documents
from app.services.file_service import FileService
from app.services.mongo_vector_service import MongoVectorService
from app.utils.config import settings

logger = logging.getLogger(__name__)


class RagService:
    """Orchestrates RAG pipeline: upload → chunk → embed → store → retrieve → generate."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.file_service = FileService(
            uploads_dir=settings.uploads_dir,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self.vector_service = MongoVectorService(db)

    async def upload_and_process_files(
        self,
        files: list[UploadFile],
    ) -> dict[str, Any]:
        """Upload files, extract text, chunk, embed, and store.

        Args:
            files: List of uploaded files

        Returns:
            Processing statistics
        """
        logger.info(f"Processing {len(files)} files")

        stats = {
            "processed_files": 0,
            "total_chunks": 0,
            "documents": [],
            "errors": [],
        }

        for file in files:
            try:
                # Save uploaded file
                saved_path = await self.file_service.save_upload(file)
                logger.info(f"Saved file: {saved_path}")

                # Process file using existing file_service
                documents = self.file_service.process_file(saved_path)

                if not documents:
                    logger.warning(f"No chunks generated from {file.filename}")
                    stats["errors"].append(f"{file.filename}: No chunks generated")
                    continue

                # Extract chunk texts and get metadata from first document
                chunk_texts = [doc.get("page_content", "") for doc in documents]
                chunk_metadata_list = [doc.get("metadata", {}) for doc in documents]
                metadata = documents[0].get("metadata", {})

                file_type = metadata.get("source_type", "unknown")
                source_priority = metadata.get("source_priority", "primary")

                # Store chunks with embeddings
                result = await self.vector_service.store_document_chunks(
                    filename=file.filename,
                    file_type=file_type,
                    path=str(saved_path),
                    chunk_texts=chunk_texts,
                    chunk_metadata_list=chunk_metadata_list,
                    source_priority=source_priority,
                )

                stats["processed_files"] += 1
                stats["total_chunks"] += result["chunks_stored"]
                stats["documents"].append(result)

                logger.info(
                    f"Successfully processed {file.filename}: "
                    f"{result['chunks_stored']} chunks stored"
                )

            except Exception as e:
                logger.error(f"Error processing {file.filename}: {e}")
                stats["errors"].append(f"{file.filename}: {str(e)}")

        logger.info(f"Upload processing complete: {stats}")
        return stats

    async def search_and_retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for relevant chunks using vector similarity.

        Args:
            query: User query or question
            top_k: Number of chunks to retrieve

        Returns:
            List of relevant chunks
        """
        logger.info(f"Retrieving top {top_k} chunks for query: {query[:100]}")

        try:
            # Search with primary source priority first
            results = await self.vector_service.search_chunks(
                query_text=query,
                top_k=top_k,
                source_priority="primary",
            )

            # If not enough primary results, add secondary
            if len(results) < top_k:
                secondary_results = await self.vector_service.search_chunks(
                    query_text=query,
                    top_k=top_k - len(results),
                    source_priority="secondary",
                )
                results.extend(secondary_results)

            logger.info(f"Retrieved {len(results)} relevant chunks")
            return results

        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []

    async def get_all_documents(self) -> list[dict[str, Any]]:
        """Get all stored documents.

        Returns:
            List of documents
        """
        try:
            documents = await self.vector_service.get_all_documents()
            logger.info(f"Retrieved {len(documents)} documents")
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    async def get_vector_store_stats(self) -> dict[str, Any]:
        """Get vector store statistics.

        Returns:
            Statistics dictionary
        """
        try:
            stats = await self.vector_service.get_stats()
            logger.info(f"Vector store stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error retrieving stats: {e}")
            return {}
