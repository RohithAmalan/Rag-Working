from __future__ import annotations

from pathlib import Path
from typing import Any
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
    def _dedupe_columns(columns: list[str]) -> list[str]:
        """Ensure column names are unique and non-empty."""
        seen: dict[str, int] = {}
        normalized: list[str] = []
        for idx, raw in enumerate(columns, start=1):
            col = str(raw).strip() if raw is not None else ""
            if not col:
                col = f"column_{idx}"
            base = col
            count = seen.get(base, 0)
            if count > 0:
                col = f"{base}_{count + 1}"
            seen[base] = count + 1
            normalized.append(col)
        return normalized

    @staticmethod
    def _promote_first_row_as_header_if_needed(df: pd.DataFrame) -> pd.DataFrame:
        """Promote first row to headers when current headers are mostly unnamed.

        This helps spreadsheets where pandas reads placeholder headers (Unnamed:*),
        but the real header row is the first data row after a title/blank area.
        """
        if df.empty:
            return df

        cols = [str(c).strip() for c in df.columns]
        unnamed_count = sum(1 for c in cols if c.lower().startswith("unnamed:"))
        if unnamed_count == 0:
            return df

        first_row = [str(v).strip() for v in df.iloc[0].tolist()]

        replaced = 0
        candidate_cols: list[str] = []
        for old_col, first_val in zip(cols, first_row):
            if old_col.lower().startswith("unnamed:"):
                # Accept likely header text only.
                if (
                    first_val
                    and first_val.lower() != "nan"
                    and not first_val.replace(".", "", 1).isdigit()
                ):
                    candidate_cols.append(first_val)
                    replaced += 1
                else:
                    candidate_cols.append(old_col)
            else:
                candidate_cols.append(old_col)

        # Promote only when this meaningfully improves unnamed headers.
        if replaced >= max(1, unnamed_count // 2):
            promoted = df.iloc[1:].copy().reset_index(drop=True)
            promoted.columns = FileService._dedupe_columns(candidate_cols)
            return promoted

        return df

    @staticmethod
    def _detect_header_row(df_raw: pd.DataFrame, max_scan: int = 10) -> int:
        """Find the row index that is most likely the real header row.

        When an Excel/CSV file has a title or blank rows before the real headers,
        pandas labels columns as 'Unnamed: N'.  We scan the first ``max_scan``
        rows and return the one that has the most non-null, non-numeric string
        cells – that row is almost certainly the true header.
        """
        unnamed_cols = sum(1 for c in df_raw.columns if str(c).startswith("Unnamed:"))
        if unnamed_cols == 0:
            return 0  # current headers already look real

        best_row = 0
        best_score = -1
        for row_idx in range(min(max_scan, len(df_raw))):
            row_vals = df_raw.iloc[row_idx]
            score = sum(
                1
                for v in row_vals
                if isinstance(v, str)
                and v.strip()
                and not v.strip().lstrip("-").replace(".", "").isdigit()
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
            return FileService._promote_first_row_as_header_if_needed(df_raw)
        # df_raw was read with header=0, so df_raw.iloc[N] = file row N+1
        # To re-read with the correct header, use header_row + 1
        df = pd.read_csv(file_path, header=header_row + 1)
        df = df.dropna(how="all").reset_index(drop=True)
        return FileService._promote_first_row_as_header_if_needed(df)

    @staticmethod
    def _read_excel_smart(file_path: Path) -> dict[str, pd.DataFrame]:
        """Read all Excel sheets, auto-detecting the real header row per sheet."""
        sheets_raw = pd.read_excel(file_path, sheet_name=None, header=0)
        result: dict[str, pd.DataFrame] = {}
        for sheet_name, df_raw in sheets_raw.items():
            header_row = FileService._detect_header_row(df_raw)
            if header_row == 0:
                result[sheet_name] = FileService._promote_first_row_as_header_if_needed(
                    df_raw
                )
            else:
                # df_raw was read with header=0, so df_raw.iloc[N] = file row N+1
                # To re-read with the correct header row, use header_row + 1
                df = pd.read_excel(
                    file_path, sheet_name=sheet_name, header=header_row + 1
                )
                df = df.dropna(how="all").reset_index(drop=True)
                result[sheet_name] = FileService._promote_first_row_as_header_if_needed(
                    df
                )
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
                    dataframe_to_documents(
                        sheet_df, file_path.name, "excel", sheet_name=str(sheet_name)
                    )
                )
            return all_docs

        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            page_texts: list[str] = []
            for page in reader.pages:
                extracted = page.extract_text() or ""
                if extracted.strip():
                    page_texts.append(extracted)
            return chunk_pdf_texts(
                file_path.name, page_texts, self.chunk_size, self.chunk_overlap
            )

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
            numeric_df = (
                df.select_dtypes(include=["number"]) if not df.empty else pd.DataFrame()
            )
            numeric = numeric_df.describe().to_dict() if not numeric_df.empty else {}
            report.update(
                {
                    "source_type": "csv",
                    "row_count": int(len(df)),
                    "column_count": int(len(df.columns)),
                    "column_names": [str(col) for col in df.columns],
                    "missing_values": {
                        str(k): int(v) for k, v in df.isna().sum().to_dict().items()
                    },
                    "sample_rows": df.head(3)
                    .fillna("unknown")
                    .to_dict(orient="records"),
                    "numeric_summary": {
                        str(col): {
                            str(metric): self._normalize_report_value(val)
                            for metric, val in values.items()
                        }
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
                    numeric_df = (
                        df.select_dtypes(include=["number"])
                        if not df.empty
                        else pd.DataFrame()
                    )
                    numeric = (
                        numeric_df.describe().to_dict() if not numeric_df.empty else {}
                    )
                    numeric_summary_primary = {
                        str(col): {
                            str(metric): self._normalize_report_value(val)
                            for metric, val in values.items()
                        }
                        for col, values in numeric.items()
                    }

                sheet_reports.append(
                    {
                        "sheet_name": str(sheet_name),
                        "row_count": int(len(df)),
                        "column_count": int(len(df.columns)),
                        "column_names": [str(col) for col in df.columns],
                        "sample_rows": (
                            df.head(2).fillna("unknown").to_dict(orient="records")
                            if not df.empty
                            else []
                        ),
                    }
                )

            # Populate root level with primary sheet details (similar to CSV format)
            report.update(
                {
                    "source_type": "excel",
                    "sheet_count": len(sheets),
                    "sheet_reports": sheet_reports,
                    "row_count": total_rows,
                    "column_names": (
                        [str(col) for col in first_sheet_df.columns]
                        if first_sheet_df is not None
                        else []
                    ),
                    "column_count": (
                        int(len(first_sheet_df.columns))
                        if first_sheet_df is not None
                        else 0
                    ),
                    "sample_rows": (
                        first_sheet_df.head(3)
                        .fillna("unknown")
                        .to_dict(orient="records")
                        if first_sheet_df is not None and not first_sheet_df.empty
                        else []
                    ),
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

    def get_file_data_preview(
        self,
        file_path: Path,
        page: int = 1,
        page_size: int = 100,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        """Get paginated file data preview for dashboard display.

        Args:
            file_path: Path to the file
            page: Page number (1-indexed)
            page_size: Number of rows per page
            sheet_name: Excel sheet name (None = first sheet)

        Returns:
            Dictionary with columns, rows, total_rows, current_page, total_pages
        """
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            df = self._read_csv_smart(file_path)
            total_rows = len(df)
            total_pages = (total_rows + page_size - 1) // page_size

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_df = df.iloc[start_idx:end_idx]

            return {
                "file_type": "csv",
                "columns": [str(col) for col in df.columns],
                "rows": page_df.fillna("").to_dict(orient="records"),
                "total_rows": total_rows,
                "current_page": page,
                "total_pages": total_pages,
                "page_size": page_size,
            }

        elif suffix == ".xlsx":
            sheets = self._read_excel_smart(file_path)

            # Use specified sheet or first sheet
            if sheet_name and sheet_name in sheets:
                df = sheets[sheet_name]
                selected_sheet = sheet_name
            else:
                selected_sheet = list(sheets.keys())[0]
                df = sheets[selected_sheet]

            total_rows = len(df)
            total_pages = (total_rows + page_size - 1) // page_size

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_df = df.iloc[start_idx:end_idx]

            return {
                "file_type": "excel",
                "sheet_names": list(sheets.keys()),
                "selected_sheet": selected_sheet,
                "columns": [str(col) for col in df.columns],
                "rows": page_df.fillna("").to_dict(orient="records"),
                "total_rows": total_rows,
                "current_page": page,
                "total_pages": total_pages,
                "page_size": page_size,
            }

        elif suffix == ".pdf":
            # For PDFs, return text content paginated by pages
            reader = PdfReader(str(file_path))
            total_pages = len(reader.pages)

            start_page = (page - 1) * page_size
            end_page = min(start_page + page_size, total_pages)

            pages_content = []
            for i in range(start_page, end_page):
                text = reader.pages[i].extract_text() or ""
                pages_content.append(
                    {
                        "page_number": i + 1,
                        "content": text.strip(),
                    }
                )

            return {
                "file_type": "pdf",
                "pages": pages_content,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": page_size,
            }

        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def get_file_analytics(
        self,
        file_path: Path,
        sheet_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate analytics and statistics for charts/graphs.

        Args:
            file_path: Path to the file
            sheet_name: Excel sheet name (None = first sheet)

        Returns:
            Dictionary with analytics data for visualization
        """
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            df = self._read_csv_smart(file_path)
            return self._generate_dataframe_analytics(df, file_path.name)

        elif suffix == ".xlsx":
            sheets = self._read_excel_smart(file_path)

            # Use specified sheet or first sheet
            if sheet_name and sheet_name in sheets:
                df = sheets[sheet_name]
                selected_sheet = sheet_name
            else:
                selected_sheet = list(sheets.keys())[0]
                df = sheets[selected_sheet]

            analytics = self._generate_dataframe_analytics(df, file_path.name)
            analytics["sheet_names"] = list(sheets.keys())
            analytics["selected_sheet"] = selected_sheet
            return analytics

        elif suffix == ".pdf":
            # For PDFs, return basic statistics
            reader = PdfReader(str(file_path))
            return {
                "file_type": "pdf",
                "file_name": file_path.name,
                "total_pages": len(reader.pages),
                "pages_with_text": len(
                    [p for p in reader.pages if (p.extract_text() or "").strip()]
                ),
                "analytics_available": False,
            }

        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    @staticmethod
    def _generate_dataframe_analytics(
        df: pd.DataFrame, file_name: str
    ) -> dict[str, Any]:
        """Generate analytics from a DataFrame for visualization."""
        analytics = {
            "file_type": "tabular",
            "file_name": file_name,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": [str(col) for col in df.columns],
            "analytics_available": True,
            "numeric_columns": [],
            "categorical_columns": [],
            "date_columns": [],
            "column_stats": {},
            "top_values": {},
        }

        # Identify column types
        for col in df.columns:
            col_str = str(col)
            dtype = df[col].dtype

            if pd.api.types.is_numeric_dtype(dtype):
                analytics["numeric_columns"].append(col_str)
                # Generate statistics for numeric columns
                analytics["column_stats"][col_str] = {
                    "min": float(df[col].min()) if not pd.isna(df[col].min()) else 0,
                    "max": float(df[col].max()) if not pd.isna(df[col].max()) else 0,
                    "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else 0,
                    "median": (
                        float(df[col].median()) if not pd.isna(df[col].median()) else 0
                    ),
                    "std": float(df[col].std()) if not pd.isna(df[col].std()) else 0,
                    "count": int(df[col].count()),
                }
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                analytics["date_columns"].append(col_str)
            else:
                analytics["categorical_columns"].append(col_str)
                # Get top 10 values for categorical columns
                value_counts = df[col].value_counts().head(10)
                analytics["top_values"][col_str] = [
                    {"name": str(k), "count": int(v)} for k, v in value_counts.items()
                ]

        # Generate correlation matrix for numeric columns (if any)
        if len(analytics["numeric_columns"]) > 1:
            numeric_df = df[analytics["numeric_columns"]].select_dtypes(
                include=[float, int]
            )
            if not numeric_df.empty:
                corr_matrix = numeric_df.corr()
                analytics["correlation"] = {
                    "columns": [str(col) for col in corr_matrix.columns],
                    "matrix": corr_matrix.fillna(0).values.tolist(),
                }

        return analytics
