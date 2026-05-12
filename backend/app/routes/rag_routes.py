from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.models.schemas import DocumentsResponse, QueryRequest, QueryResponse, SourceItem, RetrievedChunk
from app.rag.generator import generate_answer
from app.services.rag_service import RagService
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_rag_service() -> RagService:
    """Get RAG service from app state."""
    from app.main import app

    if not hasattr(app.state, "rag_service") or app.state.rag_service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "RAG service is unavailable. Check backend startup logs and configuration."
            ),
        )
    return app.state.rag_service


@router.post("/upload", response_model=dict[str, Any])
async def upload_documents(
    files: list[UploadFile] = File(...),
    rag_service: RagService = Depends(get_rag_service),
):
    """Upload and process files (PDF, CSV, XLSX).

    Args:
        files: List of files to upload
        rag_service: RAG service instance

    Returns:
        Upload processing statistics
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    try:
        result = await rag_service.upload_and_process_files(files)
        
        # Calculate chunk counts
        total_chunks = sum(doc.get("chunks_stored", 0) for doc in result.get("documents", []))
        
        return {
            "message": "Files uploaded and indexed successfully",
            "processed_files": result.get("processed_files", 0),
            "total_chunks": total_chunks,
            "documents": result.get("documents", []),
            "errors": result.get("errors", []),
        }
    except ValueError as exc:
        logger.error(f"Validation error during upload: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Upload failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(exc)}") from exc


@router.post("/query", response_model=dict[str, Any])
async def query_documents(
    payload: QueryRequest,
    rag_service: RagService = Depends(get_rag_service),
):
    """Query uploaded documents with semantic search and LLM response.

    Args:
        payload: Query request with question and top_k
        rag_service: RAG service instance

    Returns:
        Query response with answer and retrieved chunks
    """
    try:
        logger.info(f"Processing query: {payload.question[:50]}...")
        
        # Retrieve relevant chunks
        retrieved_chunks = await rag_service.search_and_retrieve(
            query=payload.question,
            top_k=payload.top_k,
        )
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

        if not retrieved_chunks:
            logger.info("No chunks retrieved, returning empty answer")
            return {
                "answer": "I don't know based on the uploaded data.",
                "retrieved_chunks": [],
                "citations": [],
            }

        # Build context from retrieved chunks
        context = "\n\n".join(
            [
                f"[{chunk.get('source', 'Unknown')}]\n{chunk.get('chunk_text', '')}"
                for chunk in retrieved_chunks
            ]
        )
        logger.debug(f"Context length: {len(context)} chars")

        # Generate LLM response
        try:
            logger.info("Calling generate_answer...")
            answer = generate_answer(
                question=payload.question,
                context=context,
                groq_api_key=settings.groq_api_key,
                groq_model=settings.groq_model,
                source_types={
                    chunk.get("metadata", {}).get("source_type", chunk.get("metadata", {}).get("file_type", "unknown"))
                    for chunk in retrieved_chunks
                },
            )
            logger.info(f"Answer generated: {answer[:50]}...")
        except ValueError as ve:
            logger.error(f"Groq configuration error: {ve}")
            raise HTTPException(
                status_code=503,
                detail="Groq API key is not configured. Set GROQ_API_KEY in environment.",
            ) from ve
        except RuntimeError as re:
            logger.error(f"Groq API error: {re}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate answer via Groq: {str(re)}",
            ) from re

        # Format retrieved chunks for response
        formatted_chunks = [
            {
                "content": chunk.get("chunk_text", ""),
                "score": chunk.get("similarity_score", 0.0),
                "metadata": {
                    **chunk.get("metadata", {}),
                    "file_name": chunk.get("metadata", {}).get("file_name", chunk.get("source", "Unknown")),
                    "source_type": chunk.get("metadata", {}).get(
                        "source_type",
                        chunk.get("metadata", {}).get("file_type", "unknown"),
                    ),
                },
            }
            for chunk in retrieved_chunks
        ]

        # Extract citations from metadata
        citations = [
            {
                "file_name": chunk.get("source", "Unknown"),
                "source_type": chunk.get("metadata", {}).get("file_type", "unknown"),
                "sheet_name": chunk.get("metadata", {}).get("sheet_name", None),
                "row_index": chunk.get("metadata", {}).get("row_index", None),
                "chunk_index": chunk.get("chunk_index", None),
            }
            for chunk in retrieved_chunks
        ]

        return {
            "answer": answer,
            "retrieved_chunks": formatted_chunks,
            "citations": citations,
        }

    except HTTPException:
        # Re-raise HTTP exceptions (ValueError, RuntimeError from Groq)
        raise
    except Exception as exc:
        logger.error(f"Query failed: {type(exc).__name__}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(exc)}") from exc


@router.get("/documents", response_model=dict[str, Any])
async def list_documents(rag_service: RagService = Depends(get_rag_service)):
    """List all uploaded documents and vector store statistics.

    Args:
        rag_service: RAG service instance

    Returns:
        Documents and statistics
    """
    try:
        documents = await rag_service.get_all_documents()
        stats = await rag_service.get_vector_store_stats()

        return {
            "total_chunks": stats.get("total_chunks", 0),
            "total_documents": stats.get("total_documents", 0),
            "documents": [
                {
                    "file_name": doc.get("filename", ""),
                    "source_type": doc.get("file_type", "unknown"),
                    "chunks": 0,  # Will be calculated from chunks collection in future
                }
                for doc in documents
            ],
            "stats": stats,
        }
    except Exception as exc:
        logger.error(f"Failed to list documents: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(exc)}") from exc
