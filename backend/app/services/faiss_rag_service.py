"""FAISS-backed fallback RAG service for offline/degraded mode."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.rag.pipeline import RagPipeline
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FaissRagService:
    """Drop-in replacement for RagService when MongoDB is unavailable."""

    def __init__(self) -> None:
        self.pipeline = RagPipeline(
            uploads_dir=settings.uploads_dir,
            vector_dir=settings.vector_dir,
            cache_file=settings.cache_file,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            openai_api_key=settings.openai_api_key,
            groq_api_key=settings.groq_api_key,
            groq_model=settings.groq_model,
        )

    def startup(self) -> None:
        self.pipeline.startup()

    async def upload_and_process_files(self, files: list[UploadFile]) -> dict[str, Any]:
        existing_docs = self.pipeline._load_cache()
        new_docs: list[dict[str, Any]] = []
        per_file_docs: list[dict[str, Any]] = []
        errors: list[str] = []

        for file in files:
            try:
                saved_path = await self.pipeline.file_service.save_upload(file)
                parsed_docs = self.pipeline.file_service.process_file(saved_path)

                if not parsed_docs:
                    errors.append(f"{file.filename}: No chunks generated")
                    continue

                new_docs.extend(parsed_docs)

                metadata = parsed_docs[0].get("metadata", {})
                per_file_docs.append(
                    {
                        "filename": file.filename,
                        "file_type": metadata.get("source_type", "unknown"),
                        "path": str(saved_path),
                        "chunks_stored": len(parsed_docs),
                        "source_priority": metadata.get("source_priority", "primary"),
                    }
                )
            except Exception as exc:
                logger.error(f"Error processing {file.filename}: {exc}")
                errors.append(f"{file.filename}: {str(exc)}")

        merged_docs = existing_docs + new_docs
        self.pipeline._save_cache(merged_docs)

        primary_docs = [
            d for d in merged_docs if d.get("metadata", {}).get("source_priority") == "primary"
        ]
        secondary_docs = [
            d for d in merged_docs if d.get("metadata", {}).get("source_priority") == "secondary"
        ]

        self.pipeline.vector_manager.rebuild(primary_docs, secondary_docs)

        return {
            "processed_files": len(per_file_docs),
            "total_chunks": len(new_docs),
            "documents": per_file_docs,
            "errors": errors,
        }

    async def search_and_retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        hits = self.pipeline.vector_manager.retrieve(query, top_k=top_k)
        results: list[dict[str, Any]] = []

        for entry in hits:
            doc = entry.get("doc", {})
            metadata = doc.get("metadata", {})
            results.append(
                {
                    "chunk_text": doc.get("page_content", ""),
                    "source": metadata.get("file_name", "unknown"),
                    "similarity_score": float(entry.get("score", 0.0)),
                    "metadata": metadata,
                    "chunk_index": metadata.get("chunk_index"),
                }
            )

        return results

    async def get_all_documents(self) -> list[dict[str, Any]]:
        docs = self.pipeline._load_cache()
        grouped: dict[tuple[str, str], int] = defaultdict(int)

        for doc in docs:
            metadata = doc.get("metadata", {})
            file_name = metadata.get("file_name", "unknown")
            source_type = metadata.get("source_type", "unknown")
            grouped[(file_name, source_type)] += 1

        return [
            {
                "filename": file_name,
                "file_type": source_type,
                "chunks": chunk_count,
            }
            for (file_name, source_type), chunk_count in sorted(grouped.items(), key=lambda x: x[0][0])
        ]

    async def get_vector_store_stats(self) -> dict[str, Any]:
        docs = self.pipeline._load_cache()
        primary = 0
        secondary = 0
        unique_files: set[str] = set()

        for doc in docs:
            metadata = doc.get("metadata", {})
            unique_files.add(metadata.get("file_name", "unknown"))
            if metadata.get("source_priority") == "primary":
                primary += 1
            else:
                secondary += 1

        return {
            "total_chunks": len(docs),
            "total_documents": len(unique_files),
            "primary_chunks": primary,
            "secondary_chunks": secondary,
            "backend": "faiss-fallback",
        }
