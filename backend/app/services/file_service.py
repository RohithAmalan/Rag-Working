from __future__ import annotations

from typing import Any
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import UploadFile
from pypdf import PdfReader

from app.rag.chunking import chunk_pdf_texts, dataframe_to_documents


class FileService:
    allowed_types = {".csv", ".xlsx", ".pdf"}

    def __init__(self, uploads_dir: Path, chunk_size: int, chunk_overlap: int):
        self.uploads_dir = uploads_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def save_upload(self, file: UploadFile) -> Path:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in self.allowed_types:
            raise ValueError(f"Unsupported file type: {suffix}")

        safe_name = f"{uuid4().hex}_{Path(file.filename or 'upload').name}"
        file_path = self.uploads_dir / safe_name

        payload = await file.read()
        file_path.write_bytes(payload)
        return file_path

    def process_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Process file and return documents with page_content and metadata."""
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            df = pd.read_csv(file_path)
            return dataframe_to_documents(df, file_path.name, "csv")

        if suffix == ".xlsx":
            all_docs: list[dict[str, Any]] = []
            sheets = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, sheet_df in sheets.items():
                all_docs.extend(
                    dataframe_to_documents(sheet_df, file_path.name, "excel", sheet_name=str(sheet_name))
                )
            return all_docs

        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            page_texts: list[str] = []
            for page in reader.pages:
                extracted = page.extract_text() or ""
                if extracted.strip():
                    page_texts.append(extracted)
            return chunk_pdf_texts(file_path.name, page_texts, self.chunk_size, self.chunk_overlap)

        raise ValueError(f"Unsupported file type: {suffix}")
