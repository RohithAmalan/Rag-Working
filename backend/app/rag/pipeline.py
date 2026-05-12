from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.models.schemas import DocumentSummary
from app.rag.embeddings import get_embeddings
from app.rag.generator import generate_answer
from app.services.file_service import FileService
from app.vectorstore.faiss_store import VectorStoreManager


class RagPipeline:
    def __init__(
        self,
        uploads_dir: Path,
        vector_dir: Path,
        cache_file: Path,
        chunk_size: int,
        chunk_overlap: int,
        openai_api_key: str,
        groq_api_key: str,
        groq_model: str,
    ):
        self.cache_file = cache_file
        self.groq_api_key = groq_api_key
        self.groq_model = groq_model

        embeddings = get_embeddings(openai_api_key)
        self.vector_manager = VectorStoreManager(vector_dir, embeddings)
        self.file_service = FileService(uploads_dir, chunk_size, chunk_overlap)

    def startup(self) -> None:
        self.vector_manager.load()

    async def ingest(self, files: list[UploadFile]) -> dict[str, int]:
        existing_docs = self._load_cache()
        new_docs: list[dict[str, Any]] = []

        for file in files:
            saved_path = await self.file_service.save_upload(file)
            parsed_docs = self.file_service.process_file(saved_path)
            new_docs.extend(parsed_docs)

        merged_docs = existing_docs + new_docs
        self._save_cache(merged_docs)

        primary_docs = [d for d in merged_docs if d.get("metadata", {}).get("source_priority") == "primary"]
        secondary_docs = [d for d in merged_docs if d.get("metadata", {}).get("source_priority") == "secondary"]

        self.vector_manager.rebuild(primary_docs, secondary_docs)

        return {
            "processed_files": len(files),
            "primary_chunks": len(primary_docs),
            "secondary_chunks": len(secondary_docs),
        }

    def ask(self, question: str, top_k: int) -> dict[str, Any]:
        hits = self.vector_manager.retrieve(question, top_k=top_k)
        if not hits:
            return {
                "answer": "I don't know based on the uploaded data.",
                "citations": [],
                "retrieved_chunks": [],
            }

        context_parts = [entry["doc"]["page_content"] for entry in hits]
        context = "\n\n".join(context_parts)
        answer = generate_answer(question, context, self.groq_api_key, self.groq_model)

        citations = []
        retrieved_chunks = []

        for entry in hits:
            doc = entry["doc"]
            score = entry["score"]
            metadata = doc.get("metadata", {})
            citations.append(
                {
                    "file_name": metadata.get("file_name", "unknown"),
                    "source_type": metadata.get("source_type", "pdf"),
                    "sheet_name": metadata.get("sheet_name"),
                    "row_index": metadata.get("row_index"),
                    "chunk_index": metadata.get("chunk_index"),
                }
            )
            retrieved_chunks.append(
                {
                    "content": doc.get("page_content", ""),
                    "score": score,
                    "metadata": metadata,
                }
            )

        return {
            "answer": answer,
            "citations": citations,
            "retrieved_chunks": retrieved_chunks,
        }

    def list_documents(self) -> tuple[dict[str, int], list[DocumentSummary]]:
        docs = self._load_cache()
        grouped: dict[tuple[str, str], int] = defaultdict(int)
        primary = 0
        secondary = 0

        for doc in docs:
            metadata = doc.get("metadata", {})
            file_name = metadata.get("file_name", "unknown")
            source_type = metadata.get("source_type", "pdf")
            grouped[(file_name, source_type)] += 1
            if metadata.get("source_priority") == "primary":
                primary += 1
            else:
                secondary += 1

        items = [
            DocumentSummary(file_name=k[0], source_type=k[1], chunks=v)
            for k, v in sorted(grouped.items(), key=lambda item: item[0][0])
        ]

        return (
            {
                "total_chunks": len(docs),
                "primary_chunks": primary,
                "secondary_chunks": secondary,
            },
            items,
        )

    def _save_cache(self, docs: list[dict[str, Any]]) -> None:
        self.cache_file.write_text(json.dumps(docs, ensure_ascii=True, indent=2), encoding="utf-8")

    def _load_cache(self) -> list[dict[str, Any]]:
        if not self.cache_file.exists():
            return []
        return json.loads(self.cache_file.read_text(encoding="utf-8"))
