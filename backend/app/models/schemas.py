from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str


class QueryRequest(BaseModel):
    question: str = Field(
        min_length=3,
        description="Natural language question about uploaded documents",
        examples=[
            "What were the total sales in March?",
            "Who is the top performing employee?",
            "Summarize the Q1 revenue by region"
        ]
    )
    top_k: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Number of relevant chunks to retrieve"
    )
    selected_file: str | None = Field(
        default=None,
        description="Optional file name to scope retrieval (e.g., 'sales.csv')",
        examples=["sales.csv", "report.pdf", None]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What were the total sales in March?",
                    "top_k": 6,
                    "selected_file": None
                },
                {
                    "question": "Who achieved the highest sales?",
                    "top_k": 10,
                    "selected_file": "sales.csv"
                }
            ]
        }
    }


class SourceItem(BaseModel):
    file_name: str
    source_type: Literal["csv", "excel", "pdf"]
    sheet_name: str | None = None
    row_index: int | None = None
    chunk_index: int | None = None


class RetrievedChunk(BaseModel):
    content: str
    score: float
    metadata: dict[str, Any]


class QueryResponse(BaseModel):
    answer: str
    citations: list[SourceItem]
    retrieved_chunks: list[RetrievedChunk]


class UploadResponse(BaseModel):
    message: str
    processed_files: int
    primary_chunks: int
    secondary_chunks: int


class DocumentSummary(BaseModel):
    file_name: str
    source_type: Literal["csv", "excel", "pdf"]
    chunks: int


class DocumentsResponse(BaseModel):
    total_chunks: int
    primary_chunks: int
    secondary_chunks: int
    documents: list[DocumentSummary]
