"""Sync locally stored FAISS chunk cache into MongoDB Atlas collections."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path

from app.db.mongo import close_mongo_connection, connect_to_mongo, get_database
from app.services.mongo_vector_service import MongoVectorService
from app.utils.config import settings


def _load_cache(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _group_by_file(cached_docs: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in cached_docs:
        metadata = item.get("metadata", {})
        file_name = metadata.get("file_name", "unknown")
        grouped[file_name].append(item)
    return grouped


async def main() -> None:
    cached_docs = _load_cache(settings.cache_file)
    if not cached_docs:
        print("No cached FAISS data found. Nothing to sync.")
        return

    grouped = _group_by_file(cached_docs)
    print(f"Found {len(grouped)} file groups in {settings.cache_file}")

    try:
        await connect_to_mongo()
    except Exception as exc:
        print("Could not connect to MongoDB Atlas. Sync aborted.")
        print(f"Reason: {exc}")
        print("Tip: check office network/firewall, Atlas IP access list, and MONGODB_URI in backend/.env")
        raise SystemExit(1)

    try:
        db = get_database()
        vector_service = MongoVectorService(db)

        existing = await vector_service.get_all_documents()
        existing_names = {doc.get("filename", "") for doc in existing}

        synced_files = 0
        skipped_files = 0

        for file_name, docs in grouped.items():
            if file_name in existing_names:
                print(f"Skipping existing file: {file_name}")
                skipped_files += 1
                continue

            docs_sorted = sorted(
                docs,
                key=lambda d: d.get("metadata", {}).get("chunk_index", 0),
            )

            first_metadata = docs_sorted[0].get("metadata", {})
            file_type = first_metadata.get("source_type", "pdf")
            source_priority = first_metadata.get("source_priority", "secondary")
            chunk_texts = [d.get("page_content", "") for d in docs_sorted]

            possible_path = settings.uploads_dir / file_name
            stored_path = str(possible_path) if possible_path.exists() else file_name

            result = await vector_service.store_document_chunks(
                filename=file_name,
                file_type=file_type,
                path=stored_path,
                chunk_texts=chunk_texts,
                source_priority=source_priority,
            )
            print(
                f"Synced {file_name}: {result.get('chunks_stored', 0)} chunks "
                f"(document_id={result.get('document_id')})"
            )
            synced_files += 1

        print("Sync complete")
        print(f"Synced files: {synced_files}")
        print(f"Skipped existing: {skipped_files}")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
