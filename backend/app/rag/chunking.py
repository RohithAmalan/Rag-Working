from __future__ import annotations

from typing import Any


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - chunk_overlap)
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start += step
    return chunks


def _normalize_cell(value) -> str:
    try:
        import pandas as pd

        if pd.isna(value):
            return "unknown"
    except Exception:
        pass

    if value is None:
        return "unknown"
    text = str(value).strip()
    return text if text else "unknown"


def dataframe_to_documents(df, file_name: str, source_type: str, sheet_name: str | None = None) -> list[dict[str, Any]]:
    """Convert DataFrame rows to documents with enhanced searchability for lookups."""
    import re as _re

    docs: list[dict[str, Any]] = []
    # Drop columns that are purely unnamed index artifacts (Unnamed: 0, Unnamed: 1, …)
    real_cols = [col for col in df.columns if not _re.fullmatch(r"Unnamed:\s*\d+", str(col).strip())]
    if real_cols:
        df = df[real_cols]
    # Drop rows where every cell is NaN/empty
    df = df.dropna(how="all").reset_index(drop=True)
    columns = [str(col).strip() for col in df.columns]

    for row_index, row in df.iterrows():
        row_dict = {}
        row_pairs = []
        row_facts = []
        lookup_keywords = []

        for col in columns:
            value = _normalize_cell(row[col])
            row_dict[col] = value
            row_pairs.append(f"{col}={value}")
            row_facts.append(f"{col} is {value}")
            
            # Add lookup keywords for common ID/identifier fields
            col_lower = col.lower()
            if "id" in col_lower and value != "unknown":
                lookup_keywords.append(f"ID lookup: {col} = {value}")
            elif "phone" in col_lower and value != "unknown":
                lookup_keywords.append(f"Phone lookup: {value}")
            elif "email" in col_lower and value != "unknown":
                lookup_keywords.append(f"Email lookup: {value}")

        semantic_sentence = "This record shows " + ", ".join(row_facts) + "."
        compact_view = " | ".join(row_pairs)

        # Create enriched searchable content with field names more prominent
        # This helps queries like "whose phone is X" or "customer with ID Y"
        enriched_fields = []
        for col in columns:
            val = row_dict[col]
            if val and val != "unknown":
                # Add field-aware versions for better semantic matching
                enriched_fields.append(f"{col.lower()}: {val}")

        enriched_text = " | ".join(enriched_fields) if enriched_fields else semantic_sentence
        lookup_section = " Lookup keywords: " + " | ".join(lookup_keywords) if lookup_keywords else ""

        content = (
            f"Business data row from {file_name}. "
            f"{semantic_sentence} "
            f"Record details: {enriched_text}.{lookup_section} "
            f"Raw row mapping: {compact_view}."
        )

        docs.append(
            {
                "page_content": content,
                "metadata": {
                    "file_name": file_name,
                    "source_type": source_type,
                    "source_priority": "primary",
                    "sheet_name": sheet_name,
                    "row_index": int(row_index),
                },
            }
        )

    return docs


def chunk_pdf_texts(file_name: str, page_texts: list[str], chunk_size: int, chunk_overlap: int) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    chunk_index = 0

    for page_idx, page_text in enumerate(page_texts):
        for piece in _chunk_text(page_text, chunk_size, chunk_overlap):
            docs.append(
                {
                    "page_content": piece,
                    "metadata": {
                        "file_name": file_name,
                        "source_type": "pdf",
                        "source_priority": "secondary",
                        "page_index": page_idx,
                        "chunk_index": chunk_index,
                    },
                }
            )
            chunk_index += 1

    return docs
