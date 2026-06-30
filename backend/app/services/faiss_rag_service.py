"""FAISS-backed fallback RAG service for offline/degraded mode."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from fastapi import UploadFile

from app.rag.pipeline import RagPipeline
from app.services.minio_service import MinioService
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
        self.minio_service = MinioService()

    @staticmethod
    def _normalize_phone(phone_str: str) -> str:
        """Strip all separators for phone matching."""
        return re.sub(r"[\s\.\-\(\)x]", "", phone_str.lower())

    @staticmethod
    def _extract_exact_terms(query_text: str) -> dict[str, list[str]]:
        """Extract alphanumeric IDs and phone-like patterns from query."""
        # Alphanumeric IDs (6+ chars, mix of letters/numbers)
        id_pattern = r"\b[a-zA-Z0-9]{6,}\b"
        ids = re.findall(id_pattern, query_text)

        # Phone-like patterns (digits with separators)
        phone_pattern = r"\b[\d\s\.\-\(\)x]+\b"
        phones = []
        for match in re.findall(phone_pattern, query_text):
            if any(c.isdigit() for c in match) and len(re.sub(r"\D", "", match)) >= 7:
                phones.append(match.strip())

        return {"ids": ids, "phones": phones}

    async def _exact_match_search(
        self, query_text: str, top_k: int
    ) -> list[dict[str, Any]]:
        """Search for exact ID/phone matches in cached documents."""
        exact_terms = self._extract_exact_terms(query_text)
        all_docs = self.pipeline._load_cache()
        matches: list[dict[str, Any]] = []

        for doc in all_docs:
            content = doc.get("page_content", "")
            metadata = doc.get("metadata", {})
            match_score = 0

            # Check ID matches
            for term_id in exact_terms.get("ids", []):
                if term_id.lower() in content.lower():
                    match_score += 100

            # Check phone matches (separator-tolerant)
            for phone in exact_terms.get("phones", []):
                normalized = self._normalize_phone(phone)
                if normalized in self._normalize_phone(content):
                    match_score += 100

            if match_score > 0:
                matches.append(
                    {
                        "chunk_text": content,
                        "source": metadata.get("file_name", "unknown"),
                        "similarity_score": float(match_score),
                        "metadata": metadata,
                        "chunk_index": metadata.get("chunk_index"),
                    }
                )

        return sorted(matches, key=lambda x: x["similarity_score"], reverse=True)[
            :top_k
        ]

    def startup(self) -> None:
        self.pipeline.startup()

    async def upload_and_process_files(self, files: list[UploadFile]) -> dict[str, Any]:
        existing_docs = self.pipeline._load_cache()
        new_docs: list[dict[str, Any]] = []
        per_file_docs: list[dict[str, Any]] = []
        errors: list[str] = []

        for file in files:
            saved_path = None
            try:
                saved_path = await self.pipeline.file_service.save_upload(file)
                storage_info = self.minio_service.upload_file(
                    saved_path, file.filename or saved_path.name
                )
                if (
                    settings.minio_enabled
                    and storage_info.get("storage_backend") != "minio"
                ):
                    raise RuntimeError(
                        "MinIO is enabled, but object upload failed. Local storage is disabled for uploads."
                    )
                file_report = self.pipeline.file_service.analyze_file(saved_path)
                parsed_docs = self.pipeline.file_service.process_file(saved_path)

                if not parsed_docs:
                    errors.append(f"{file.filename}: No chunks generated")
                    continue

                for doc in parsed_docs:
                    metadata = doc.setdefault("metadata", {})
                    metadata.setdefault(
                        "storage_backend", storage_info.get("storage_backend", "local")
                    )
                    metadata.setdefault(
                        "storage_bucket", storage_info.get("storage_bucket", "")
                    )
                    metadata.setdefault(
                        "storage_object", storage_info.get("storage_object", "")
                    )
                    metadata.setdefault(
                        "storage_url", storage_info.get("storage_url", "")
                    )
                    metadata.setdefault(
                        "storage_path",
                        storage_info.get("storage_path", str(saved_path)),
                    )

                new_docs.extend(parsed_docs)

                metadata = parsed_docs[0].get("metadata", {})
                per_file_docs.append(
                    {
                        "filename": file.filename,
                        "file_type": metadata.get("source_type", "unknown"),
                        "path": storage_info.get("storage_path", str(saved_path)),
                        "chunks_stored": len(parsed_docs),
                        "source_priority": metadata.get("source_priority", "primary"),
                        "storage_backend": storage_info.get("storage_backend", "local"),
                        "storage_url": storage_info.get("storage_url", ""),
                        "analysis_report": file_report,
                    }
                )

            except Exception as exc:
                logger.error(f"Error processing {file.filename}: {exc}")
                errors.append(f"{file.filename}: {str(exc)}")
            finally:
                if saved_path is not None and saved_path.exists():
                    try:
                        saved_path.unlink(missing_ok=True)
                    except Exception as unlink_exc:
                        logger.warning(
                            f"Could not remove local temp file {saved_path}: {unlink_exc}"
                        )

        merged_docs = existing_docs + new_docs
        self.pipeline._save_cache(merged_docs)

        primary_docs = [
            d
            for d in merged_docs
            if d.get("metadata", {}).get("source_priority") == "primary"
        ]
        secondary_docs = [
            d
            for d in merged_docs
            if d.get("metadata", {}).get("source_priority") == "secondary"
        ]

        self.pipeline.vector_manager.rebuild(primary_docs, secondary_docs)

        return {
            "processed_files": len(per_file_docs),
            "total_chunks": len(new_docs),
            "documents": per_file_docs,
            "errors": errors,
        }

    async def search_and_retrieve(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        # Try exact match first
        exact_matches = await self._exact_match_search(query, top_k)
        if exact_matches:
            logger.info(f"Found {len(exact_matches)} exact matches for query")
            return exact_matches

        # Fall back to vector search
        logger.info("No exact matches found, falling back to vector search")
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
        grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {
                "chunks": 0,
                "path": "",
                "storage_backend": "local",
                "storage_url": "",
            }
        )

        for doc in docs:
            metadata = doc.get("metadata", {})
            file_name = metadata.get("file_name", "unknown")
            source_type = metadata.get("source_type", "unknown")
            key = (file_name, source_type)
            grouped[key]["chunks"] += 1

            if not grouped[key]["path"]:
                grouped[key]["path"] = metadata.get("storage_path", "")
            if not grouped[key]["storage_url"]:
                grouped[key]["storage_url"] = metadata.get("storage_url", "")
            if grouped[key]["storage_backend"] == "local":
                grouped[key]["storage_backend"] = metadata.get(
                    "storage_backend", "local"
                )

        return [
            {
                "filename": file_name,
                "file_type": source_type,
                "path": info.get("path", ""),
                "chunks": info.get("chunks", 0),
                "metadata": {
                    "storage_backend": info.get("storage_backend", "local"),
                    "storage_url": info.get("storage_url", ""),
                    "chunks_stored": info.get("chunks", 0),
                },
            }
            for (file_name, source_type), info in sorted(
                grouped.items(), key=lambda x: x[0][0]
            )
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
