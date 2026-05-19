"""RAG service orchestrating the complete pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.rag.chunking import chunk_pdf_texts, dataframe_to_documents
from app.services.file_service import FileService
from app.services.minio_service import MinioService
from app.services.mongo_vector_service import MongoVectorService
from app.services.langgraph_rag_service import LangGraphRAGService
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
        self.minio_service = MinioService()
        self.vector_service = MongoVectorService(db)
        
        # Initialize LangGraph RAG service with configured workflow mode
        workflow_mode = settings.langgraph_workflow_mode
        if workflow_mode not in ["basic", "advanced", "multi_agent"]:
            logger.warning(
                f"Invalid workflow mode '{workflow_mode}', defaulting to 'multi_agent'"
            )
            workflow_mode = "multi_agent"
        
        self.langgraph_service = LangGraphRAGService(
            self.vector_service,
            workflow_mode=workflow_mode,
        )
        logger.info(f"RagService initialized with LangGraph workflow mode: {workflow_mode}")

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
            saved_path = None
            try:
                # Save uploaded file
                saved_path = await self.file_service.save_upload(file)
                logger.info(f"Saved file: {saved_path}")

                storage_info = self.minio_service.upload_file(saved_path, file.filename or saved_path.name)
                if settings.minio_enabled and storage_info.get("storage_backend") != "minio":
                    raise RuntimeError(
                        "MinIO is enabled, but object upload failed. Local storage is disabled for uploads."
                    )
                file_report = self.file_service.analyze_file(saved_path)

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
                    path=storage_info.get("storage_path", str(saved_path)),
                    chunk_texts=chunk_texts,
                    chunk_metadata_list=chunk_metadata_list,
                    source_priority=source_priority,
                    document_metadata={
                        **storage_info,
                        "analysis_report": file_report,
                        "chunks_stored": len(chunk_texts),
                    },
                )

                stats["processed_files"] += 1
                stats["total_chunks"] += result["chunks_stored"]
                stats["documents"].append({
                    **result,
                    "storage_backend": storage_info.get("storage_backend", "local"),
                    "analysis_report": file_report,
                })

                logger.info(
                    f"Successfully processed {file.filename}: "
                    f"{result['chunks_stored']} chunks stored"
                )

            except Exception as e:
                logger.error(f"Error processing {file.filename}: {e}")
                stats["errors"].append(f"{file.filename}: {str(e)}")
            finally:
                if saved_path is not None and saved_path.exists():
                    try:
                        saved_path.unlink(missing_ok=True)
                    except Exception as unlink_exc:
                        logger.warning(f"Could not remove local temp file {saved_path}: {unlink_exc}")

        logger.info(f"Upload processing complete: {stats}")
        return stats

    async def search_and_retrieve(
        self,
        query: str,
        top_k: int = 5,
        file_name: str | None = None,
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
                required_file_name=file_name,
            )

            # If we already have a strong exact/structured primary match,
            # avoid diluting the answer with secondary support chunks.
            has_strong_primary_match = any(
                float(result.get("similarity_score", 0.0)) >= 0.95
                for result in results
            )

            # If not enough primary results, add secondary
            if len(results) < top_k and not has_strong_primary_match:
                secondary_results = await self.vector_service.search_chunks(
                    query_text=query,
                    top_k=top_k - len(results),
                    source_priority="secondary",
                    required_file_name=file_name,
                )
                results.extend(secondary_results)

            # Safety net: if an exact/strong primary hit exists, only return
            # primary chunks even if a secondary expansion happened.
            if any(float(result.get("similarity_score", 0.0)) >= 0.95 for result in results):
                primary_only = [
                    result
                    for result in results
                    if result.get("metadata", {}).get("source_priority") == "primary"
                ]
                if primary_only:
                    results = primary_only[:top_k]

            logger.info(f"Retrieved {len(results)} relevant chunks")
            return results

        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []

    async def query_with_langgraph(
        self,
        query: str,
        top_k: int = 15,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        """Query using LangGraph orchestrated workflow (Phase 1).
        
        This method uses the LangGraph state machine to orchestrate:
        1. Query analysis (intent detection, entity extraction)
        2. Hybrid retrieval (exact match + vector search + ranking)
        3. Answer generation with citations
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve
            file_name: Optional file name to scope search
            
        Returns:
            dict with answer, chunks, citations, confidence, and metadata
        """
        logger.info(f"LangGraph query: {query[:100]}... (file={file_name}, top_k={top_k})")
        
        try:
            result = await self.langgraph_service.query(
                question=query,
                selected_file=file_name,
                top_k=top_k,
            )
            
            logger.info(
                f"LangGraph result: confidence={result.get('confidence', 0):.2f}, "
                f"chunks={len(result.get('retrieved_chunks', []))}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"LangGraph query failed: {e}", exc_info=True)
            return {
                "answer": "I encountered an error processing your query.",
                "retrieved_chunks": [],
                "citations": [],
                "confidence": 0.0,
                "metadata": {
                    "error": str(e),
                },
            }

    async def delete_document(self, document_id: str) -> dict[str, Any]:
        """Delete document metadata, chunks, and MinIO object when available."""
        doc = await self.vector_service.get_document_by_id(document_id)
        if not doc:
            raise ValueError("Document not found")

        storage_object = str(doc.get("metadata", {}).get("storage_object", "")).strip()
        deleted_from_minio = False
        if storage_object:
            deleted_from_minio = self.minio_service.delete_object(storage_object)

        deleted_chunks = await self.vector_service.delete_document_and_chunks(document_id)

        return {
            "document_id": document_id,
            "file_name": doc.get("filename", "unknown"),
            "deleted_chunks": deleted_chunks,
            "deleted_from_minio": deleted_from_minio,
        }

    async def delete_documents_by_filename(self, file_name: str) -> dict[str, Any]:
        """Delete all versions of a file by filename from MongoDB and MinIO."""
        docs = await self.vector_service.get_documents_by_filename(file_name)
        if not docs:
            raise ValueError("Document not found")

        total_chunks = 0
        deleted_from_minio = 0
        deleted_docs = 0

        for doc in docs:
            storage_object = str(doc.get("metadata", {}).get("storage_object", "")).strip()
            if storage_object and self.minio_service.delete_object(storage_object):
                deleted_from_minio += 1

            deleted_chunks = await self.vector_service.delete_document_and_chunks(doc.get("_id", ""))
            total_chunks += deleted_chunks
            deleted_docs += 1

        return {
            "file_name": file_name,
            "deleted_documents": deleted_docs,
            "deleted_chunks": total_chunks,
            "deleted_from_minio": deleted_from_minio,
        }

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
            if hasattr(self.vector_service, "get_vector_store_stats"):
                stats = await self.vector_service.get_vector_store_stats()
            else:
                stats = await self.vector_service.get_stats()
            logger.info(f"Vector store stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error retrieving stats: {e}")
            return {}
