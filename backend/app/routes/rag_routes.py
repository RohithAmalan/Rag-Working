from typing import Any
from urllib.parse import unquote

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
            file_name=payload.selected_file,
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

    except ValueError as exc:
        logger.error(f"Query validation failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        # Re-raise HTTP exceptions (ValueError, RuntimeError from Groq)
        raise
    except Exception as exc:
        logger.error(f"Query failed: {type(exc).__name__}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(exc)}") from exc


@router.post("/query-langgraph", response_model=dict[str, Any])
async def query_with_langgraph(
    payload: QueryRequest,
    rag_service: RagService = Depends(get_rag_service),
):
    """Query documents using LangGraph orchestrated workflow (Phase 1).
    
    This endpoint uses LangGraph state machine for:
    - Query intent analysis
    - Hybrid retrieval (exact + vector + ranking)
    - Answer generation with citations
    - Confidence scoring
    
    Args:
        payload: Query request with question, top_k, and selected_file
        rag_service: RAG service instance
        
    Returns:
        Enhanced response with answer, chunks, citations, confidence, and workflow metadata
    """
    try:
        logger.info(f"LangGraph query: {payload.question[:50]}... (file={payload.selected_file})")
        
        # Execute LangGraph workflow
        result = await rag_service.query_with_langgraph(
            query=payload.question,
            top_k=payload.top_k,
            file_name=payload.selected_file,
        )
        
        # Format retrieved chunks for response
        formatted_chunks = [
            {
                "content": chunk.get("chunk_text", ""),
                "score": chunk.get("similarity_score", 0.0),
                "metadata": {
                    **chunk.get("metadata", {}),
                    "file_name": chunk.get("metadata", {}).get("file_name", "Unknown"),
                    "source_type": chunk.get("metadata", {}).get("source_type", "unknown"),
                },
            }
            for chunk in result.get("retrieved_chunks", [])
        ]
        
        return {
            "answer": result.get("answer", "I don't know based on the uploaded data."),
            "retrieved_chunks": formatted_chunks,
            "citations": result.get("citations", []),
            "confidence": result.get("confidence", 0.0),
            "metadata": result.get("metadata", {}),
        }
        
    except Exception as exc:
        logger.error(f"LangGraph query failed: {type(exc).__name__}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph query failed: {str(exc)}"
        ) from exc


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
                    "document_id": doc.get("_id", ""),
                    "file_name": doc.get("filename", ""),
                    "source_type": doc.get("file_type", "unknown"),
                    "chunks": doc.get("metadata", {}).get("chunks_stored", 0),
                    "storage_backend": doc.get("metadata", {}).get("storage_backend", "local"),
                    "storage_path": doc.get("path", ""),
                    "storage_url": doc.get("metadata", {}).get("storage_url", ""),
                    "analysis_report": doc.get("metadata", {}).get("analysis_report", {}),
                }
                for doc in documents
            ],
            "stats": stats,
        }
    except Exception as exc:
        logger.error(f"Failed to list documents: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(exc)}") from exc


@router.delete("/documents/{document_id}", response_model=dict[str, Any])
async def delete_document(document_id: str, rag_service: RagService = Depends(get_rag_service)):
    """Delete one uploaded document from MongoDB and MinIO."""
    try:
        result = await rag_service.delete_document(document_id)
        return {
            "message": "Document deleted successfully",
            **result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to delete document {document_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(exc)}") from exc


@router.delete("/documents/by-name/{file_name}", response_model=dict[str, Any])
async def delete_document_by_name(file_name: str, rag_service: RagService = Depends(get_rag_service)):
    """Delete all uploaded versions of a file by original filename."""
    try:
        decoded_name = unquote(file_name)
        result = await rag_service.delete_documents_by_filename(decoded_name)
        return {
            "message": "Document(s) deleted successfully",
            **result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to delete documents by name {file_name}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document(s): {str(exc)}") from exc


@router.get("/documents/preview/{file_name}", response_model=dict[str, Any])
async def get_file_preview(
    file_name: str,
    page: int = 1,
    page_size: int = 100,
    sheet_name: str | None = None,
    rag_service: RagService = Depends(get_rag_service),
):
    """Get paginated preview of file data for dashboard display.
    
    Args:
        file_name: Name of the uploaded file
        page: Page number (1-indexed)
        page_size: Number of rows per page
        sheet_name: Excel sheet name (optional, defaults to first sheet)
        rag_service: RAG service instance
    
    Returns:
        File data with columns, rows, and pagination info
    """
    import tempfile
    from pathlib import Path
    
    try:
        decoded_name = unquote(file_name)
        logger.info(f"Preview request for file: {decoded_name}")
        
        # Get document metadata to find file storage info
        documents = await rag_service.get_all_documents()
        logger.info(f"Found {len(documents)} documents")
        if documents:
            logger.info(f"First document filename: {documents[0].get('filename')}")
            logger.info(f"Looking for: {decoded_name}")
        
        doc = next((d for d in documents if d.get("filename") == decoded_name), None)
        
        if not doc:
            logger.warning(f"Document not found. Available files: {[d.get('filename') for d in documents]}")
            raise HTTPException(status_code=404, detail=f"File not found: {decoded_name}")
        
        storage_backend = doc.get("metadata", {}).get("storage_backend", "local")
        temp_file = None
        
        try:
            if storage_backend == "minio":
                # Download from MinIO to temporary file
                storage_object = doc.get("metadata", {}).get("storage_object")
                if not storage_object:
                    # Try to parse from storage_path (which is stored as 'path' field)
                    storage_path = doc.get("path", "")
                    if storage_path.startswith("s3://"):
                        # Parse s3://bucket/object_name -> extract object_name
                        parts = storage_path.replace("s3://", "").split("/", 1)
                        storage_object = parts[1] if len(parts) > 1 else ""
                        
                if not storage_object:
                    raise HTTPException(status_code=404, detail="MinIO object name not found in metadata")
                
                # Create temp file with same extension
                suffix = Path(decoded_name).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_path = Path(temp_file.name)
                temp_file.close()
                
                # Download file from MinIO
                success = rag_service.minio_service.download_file(storage_object, temp_path)
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to download file from MinIO")
                
                file_path_obj = temp_path
            else:
                # Local storage
                file_path = doc.get("path") or doc.get("storage_path")
                if not file_path:
                    raise HTTPException(status_code=404, detail="File path not found in metadata")
                
                file_path_obj = Path(file_path)
                
                if not file_path_obj.exists():
                    raise HTTPException(status_code=404, detail=f"File not found on disk: {file_path}")
            
            # Get file preview using file service
            preview_data = rag_service.file_service.get_file_data_preview(
                file_path=file_path_obj,
                page=page,
                page_size=page_size,
                sheet_name=sheet_name,
            )
            
            return {
                "file_name": decoded_name,
                **preview_data,
            }
        
        finally:
            # Clean up temp file if it was created
            if temp_file and Path(temp_file.name).exists():
                try:
                    Path(temp_file.name).unlink()
                except Exception as exc:
                    logger.warning(f"Failed to clean up temp file {temp_file.name}: {exc}")
        
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to get file preview for {file_name}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to get file preview: {str(exc)}") from exc


@router.get("/documents/analytics/{file_name}", response_model=dict[str, Any])
async def get_file_analytics(
    file_name: str,
    sheet_name: str | None = None,
    rag_service: RagService = Depends(get_rag_service),
):
    """Get analytics and statistics for charts/graphs visualization.
    
    Args:
        file_name: Name of the uploaded file
        sheet_name: Excel sheet name (optional, defaults to first sheet)
        rag_service: RAG service instance
    
    Returns:
        Analytics data with statistics and metrics for visualization
    """
    import tempfile
    from pathlib import Path
    
    try:
        decoded_name = unquote(file_name)
        logger.info(f"Analytics request for file: {decoded_name}")
        
        # Get document metadata to find file storage info
        documents = await rag_service.get_all_documents()
        doc = next((d for d in documents if d.get("filename") == decoded_name), None)
        
        if not doc:
            raise HTTPException(status_code=404, detail=f"File not found: {decoded_name}")
        
        storage_backend = doc.get("metadata", {}).get("storage_backend", "local")
        temp_file = None
        
        try:
            if storage_backend == "minio":
                # Download from MinIO to temporary file
                storage_object = doc.get("metadata", {}).get("storage_object")
                if not storage_object:
                    # Try to parse from storage_path (which is stored as 'path' field)
                    storage_path = doc.get("path", "")
                    if storage_path.startswith("s3://"):
                        # Parse s3://bucket/object_name -> extract object_name
                        parts = storage_path.replace("s3://", "").split("/", 1)
                        storage_object = parts[1] if len(parts) > 1 else ""
                        
                if not storage_object:
                    raise HTTPException(status_code=404, detail="MinIO object name not found in metadata")
                
                # Create temp file with same extension
                suffix = Path(decoded_name).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_path = Path(temp_file.name)
                temp_file.close()
                
                # Download file from MinIO
                success = rag_service.minio_service.download_file(storage_object, temp_path)
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to download file from MinIO")
                
                file_path_obj = temp_path
            else:
                # Local storage
                file_path = doc.get("path") or doc.get("storage_path")
                if not file_path:
                    raise HTTPException(status_code=404, detail="File path not found in metadata")
                
                file_path_obj = Path(file_path)
                
                if not file_path_obj.exists():
                    raise HTTPException(status_code=404, detail=f"File not found on disk: {file_path}")
            
            # Get analytics using file service
            analytics_data = rag_service.file_service.get_file_analytics(
                file_path=file_path_obj,
                sheet_name=sheet_name,
            )
            
            return {
                "file_name": decoded_name,
                **analytics_data,
            }
        
        finally:
            # Clean up temp file if it was created
            if temp_file and Path(temp_file.name).exists():
                try:
                    Path(temp_file.name).unlink()
                except Exception as exc:
                    logger.warning(f"Failed to clean up temp file {temp_file.name}: {exc}")
        
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to get file analytics for {file_name}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to get file analytics: {str(exc)}") from exc
