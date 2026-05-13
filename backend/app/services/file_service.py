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

    @staticmethod
    def _detect_header_row(df_raw: pd.DataFrame, max_scan: int = 10) -> int:
        """Find the row index that is most likely the real header row.

        When an Excel/CSV file has a title or blank rows before the real headers,
        pandas labels columns as 'Unnamed: N'.  We scan the first ``max_scan``
        rows and return the one that has the most non-null, non-numeric string
        cells – that row is almost certainly the true header.
        """
        unnamed_cols = sum(1 for c in df_raw.columns if str(c).startswith("Unnamed:"))
        if unnamed_cols < len(df_raw.columns) * 0.5:
            return 0  # current headers already look real

        best_row = 0
        best_score = -1
        for row_idx in range(min(max_scan, len(df_raw))):
            row_vals = df_raw.iloc[row_idx]
            score = sum(
                1
                for v in row_vals
                if isinstance(v, str) and v.strip() and not v.strip().lstrip("-").replace(".", "").isdigit()
            )
            if score > best_score:
                best_score = score
                best_row = row_idx

        return best_row

    @staticmethod
    def _read_csv_smart(file_path: Path) -> pd.DataFrame:
        """Read CSV, auto-detecting the real header row if needed."""
        df_raw = pd.read_csv(file_path, header=0)
        header_row = FileService._detect_header_row(df_raw)
        if header_row == 0:
            return df_raw
        df = pd.read_csv(file_path, header=header_row)
        return df.dropna(how="all").reset_index(drop=True)

    @staticmethod
    def _read_excel_smart(file_path: Path) -> dict[str, pd.DataFrame]:
        """Read all Excel sheets, auto-detecting the real header row per sheet."""
        sheets_raw = pd.read_excel(file_path, sheet_name=None, header=0)
        result: dict[str, pd.DataFrame] = {}
        for sheet_name, df_raw in sheets_raw.items():
            header_row = FileService._detect_header_row(df_raw)
            if header_row == 0:
                result[sheet_name] = df_raw
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
                result[sheet_name] = df.dropna(how="all").reset_index(drop=True)
        return result

    def process_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Process file and return documents with page_content and metadata."""
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            df = self._read_csv_smart(file_path)
            return dataframe_to_documents(df, file_path.name, "csv")

        if suffix == ".xlsx":
            all_docs: list[dict[str, Any]] = []
            sheets = self._read_excel_smart(file_path)
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

    @staticmethod
    def _normalize_report_value(value: Any) -> Any:
        """Convert numpy/pandas scalar values to JSON-safe Python values."""
        try:
            if hasattr(value, "item"):
                return value.item()
        except Exception:
            pass
        return value

    def analyze_file(self, file_path: Path) -> dict[str, Any]:
        """Generate a compact analysis report for uploaded files."""
        suffix = file_path.suffix.lower()
        report: dict[str, Any] = {
            "file_size_bytes": file_path.stat().st_size,
            "source_type": "unknown",
        }

        if suffix == ".csv":
            df = self._read_csv_smart(file_path)
            numeric = df.select_dtypes(include=["number"]).describe().to_dict() if not df.empty else {}
            report.update(
                {
                    "source_type": "csv",
                    "row_count": int(len(df)),
                    "column_count": int(len(df.columns)),
                    "column_names": [str(col) for col in df.columns],
                    "missing_values": {str(k): int(v) for k, v in df.isna().sum().to_dict().items()},
                    "sample_rows": df.head(3).fillna("unknown").to_dict(orient="records"),
                    "numeric_summary": {
                        str(col): {str(metric): self._normalize_report_value(val) for metric, val in values.items()}
                        for col, values in numeric.items()
                    },
                }
            )
            return report

        if suffix == ".xlsx":
            sheets = self._read_excel_smart(file_path)
            sheet_reports: list[dict[str, Any]] = []
            total_rows = 0
            
            # Extract details from first sheet (primary analysis)
            first_sheet_df = None
            first_sheet_name = None
            numeric_summary_primary = {}
            
            for sheet_name, df in sheets.items():
                total_rows += int(len(df))
                
                # Capture first sheet for root-level details
                if first_sheet_df is None:
                    first_sheet_df = df
                    first_sheet_name = sheet_name
                    numeric = df.select_dtypes(include=["number"]).describe().to_dict() if not df.empty else {}
                    numeric_summary_primary = {
                        str(col): {str(metric): self._normalize_report_value(val) for metric, val in values.items()}
                        for col, values in numeric.items()
                    }
                
                sheet_reports.append(
                    {
                        "sheet_name": str(sheet_name),
                        "row_count": int(len(df)),
                        "column_count": int(len(df.columns)),
                        "column_names": [str(col) for col in df.columns],
                        "sample_rows": df.head(2).fillna("unknown").to_dict(orient="records") if not df.empty else [],
                    }
                )

            # Populate root level with primary sheet details (similar to CSV format)
            report.update(
                {
                    "source_type": "excel",
                    "sheet_count": len(sheets),
                    "sheet_reports": sheet_reports,
                    "row_count": total_rows,
                    "column_names": [str(col) for col in first_sheet_df.columns] if first_sheet_df is not None else [],
                    "column_count": int(len(first_sheet_df.columns)) if first_sheet_df is not None else 0,
                    "sample_rows": first_sheet_df.head(3).fillna("unknown").to_dict(orient="records") if first_sheet_df is not None and not first_sheet_df.empty else [],
                    "numeric_summary": numeric_summary_primary,
                }
            )
            return report

        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
            non_empty = [txt for txt in page_texts if txt]
            report.update(
                {
                    "source_type": "pdf",
                    "page_count": len(reader.pages),
                    "pages_with_text": len(non_empty),
                    "character_count": sum(len(txt) for txt in non_empty),
                }
            )
            return report

        return report
