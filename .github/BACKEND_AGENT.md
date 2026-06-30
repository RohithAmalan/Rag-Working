# Backend AI Agent Instructions

You are working on the **backend** of a production-style RAG application.

==================================================
🎯 PROJECT PURPOSE
==================================================

Build a scalable FastAPI backend for a Retrieval-Augmented Generation (RAG) system.

Main data sources:
- CSV files (PRIMARY)
- Excel files (PRIMARY)
- PDF files (SECONDARY)

The system must support:
- dynamic uploads
- vector search
- semantic retrieval
- LLM-based responses
- Keycloak SSO authentication
- Role-based access control (RBAC)

==================================================
🧠 TECH STACK
==================================================

Backend:
- Python 3.10+
- FastAPI
- LangChain & LangGraph
- MongoDB (vector search + metadata)
- MinIO (object storage)
- Pandas (CSV/Excel processing)
- PyPDF (PDF extraction)
- Groq API (LLM)
- sentence-transformers (embeddings)
- FAISS-CPU (vector similarity)
- Keycloak (OAuth2/OIDC authentication)
- python-jose (JWT validation)
- Motor (async MongoDB driver)

==================================================
📂 ARCHITECTURE RULES
==================================================

Follow modular architecture.

Preferred structure:

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── routes/                 # API endpoints
│   │   ├── auth_routes.py     # Authentication endpoints
│   │   ├── rag_routes.py      # RAG endpoints (upload, query)
│   │   └── evaluation_routes.py # RAG evaluation endpoints
│   ├── services/               # Business logic
│   │   ├── file_service.py    # File upload & processing
│   │   ├── embedding_service.py # Embeddings generation
│   │   ├── minio_service.py   # Object storage
│   │   ├── mongo_vector_service.py # Vector search
│   │   └── keycloak_service.py # SSO integration
│   ├── rag/                    # RAG pipeline
│   │   ├── pipeline.py        # Traditional RAG
│   │   ├── langgraph_pipeline.py # LangGraph RAG
│   │   ├── chunking.py        # Text chunking
│   │   ├── embeddings.py      # Embedding strategies
│   │   ├── generator.py       # LLM response generation
│   │   ├── reranker.py        # Result reranking
│   │   └── evaluator.py       # RAG evaluation (RAGAS)
│   ├── utils/                  # Utilities
│   │   ├── config.py          # Environment config
│   │   ├── logger.py          # Logging setup
│   │   └── dependencies.py    # FastAPI dependencies
│   ├── models/                 # Pydantic models
│   │   └── schemas.py         # Request/response schemas
│   └── db/                     # Database
│       ├── mongo.py           # MongoDB connection
│       └── collections.py     # Collection helpers
├── tests/                      # Unit tests
├── uploads/                    # Local file storage
├── vectorstore/                # FAISS indices
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
└── pytest.ini                  # Test configuration
```

Rules:
- Keep files small and reusable (< 300 lines)
- Avoid monolithic logic
- Separate business logic from routes
- Use service classes/functions
- Use reusable utility modules
- One responsibility per file

==================================================
⚙️ API REQUIREMENTS
==================================================

Implement these endpoints:

**Authentication**:
- POST /auth/login - Keycloak login
- POST /auth/refresh - Token refresh
- GET /auth/userinfo - Get user info

**RAG Operations**:
- POST /upload - Upload files (CSV/Excel/PDF)
- POST /query - RAG query with context retrieval
- GET /documents - List uploaded documents
- DELETE /documents/{id} - Delete document

**Health & Status**:
- GET /health - Health check
- GET /status - System status

Best Practices:
- Use Pydantic validation for all inputs
- Return proper HTTP status codes (200, 201, 400, 401, 403, 404, 500)
- Use structured JSON responses with consistent format
- Include error messages with details
- Add request/response examples in docstrings
- Implement proper CORS configuration
- Add rate limiting for production

==================================================
📊 CSV / EXCEL RULES
==================================================

CSV/Excel are PRIMARY RAG sources.

**Processing Pipeline**:
1. Read file with pandas
2. Detect headers automatically
3. Handle missing values
4. Deduplicate column names
5. Convert rows to semantic text
6. Generate embeddings
7. Store in MongoDB vector collection

**Semantic Conversion Example**:

Input row:
```
| Employee | Sales | Month   | Region |
|----------|-------|---------|--------|
| Rohith   | 45000 | March   | West   |
```

Converted semantic chunk:
```
"Employee Rohith achieved sales of 45000 in March in the West region."
```

**Important Rules**:
- Preserve row relationships
- Include column names in semantic text
- Maintain data types and context
- Add file metadata (filename, row number)
- Handle large files in chunks (10k rows at a time)
- Support incremental uploads

==================================================
📄 PDF RULES
==================================================

PDFs are SECONDARY context sources.

**Processing Pipeline**:
1. Extract text with PyPDF
2. Clean and normalize text
3. Split into chunks (500-1000 tokens)
4. Use overlap chunking (50-100 tokens)
5. Preserve document structure
6. Track page numbers as metadata

**Chunking Strategy**:
- Recursive character splitting
- Semantic chunking for better context
- Preserve paragraphs when possible
- Include metadata: page, section, filename

==================================================
🧠 RAG RULES
==================================================

**Pipeline Architecture**:

```
User Query
    ↓
Query Expansion (optional)
    ↓
Embedding Generation
    ↓
Hybrid Search (vector + keyword)
    ↓
Result Filtering (file hints, date ranges)
    ↓
Reranking (relevance scoring)
    ↓
Context Building
    ↓
LLM Generation (Groq)
    ↓
Citation Generation
    ↓
Response to User
```

**Requirements**:
- Use top-k retrieval (k=5-10)
- Prioritize CSV/Excel chunks over PDF
- Implement hybrid search (vector + BM25)
- Add query expansion for better recall
- Use reranking for precision
- Avoid hallucination with strict prompts
- Include citations with source metadata

**Strict System Prompt**:
```
You are a helpful AI assistant that answers questions based ONLY on the provided context.

RULES:
1. Answer ONLY using information from the provided context
2. If the answer is not in the context, say "I don't have enough information to answer this question based on the uploaded documents"
3. Always cite your sources by mentioning the filename and relevant details
4. Do not make up or infer information not present in the context
5. Be precise and concise
6. If multiple sources mention the same information, cite all of them

Context:
{context}

Question: {question}

Answer:
```

==================================================
🗄 DATABASE RULES
==================================================

**MongoDB Collections**:

1. **uploaded_files** - File metadata
   - filename, file_type, upload_date
   - user_id, file_size, status
   - minio_path (if using object storage)

2. **document_chunks** - Vector embeddings
   - text, embedding (vector)
   - metadata (filename, row_num, page_num)
   - file_id (reference to uploaded_files)

3. **chat_history** - Conversation logs
   - user_id, query, response
   - context_used, timestamp

4. **users** - User records (if not using Keycloak only)
   - username, email, roles
   - created_at, last_login

**Vector Search**:
- Use MongoDB Atlas Vector Search
- Index: vector embeddings with cosine similarity
- Hybrid search: combine vector + text search
- Store 384-dim embeddings (sentence-transformers)

**Never confuse**:
- MongoDB = Metadata + Vector Search
- FAISS = Fallback vector store (if not using MongoDB Atlas)
- MinIO = Object storage for files

==================================================
🔐 AUTHENTICATION & AUTHORIZATION
==================================================

**Keycloak Integration**:
- Use OAuth2/OIDC flow
- Validate JWT tokens on protected endpoints
- Extract user info from token claims
- Implement role-based access control (RBAC)

**Roles**:
- `admin` - Full access (upload, query, delete, admin operations)
- `analyst` - Read + query access
- `viewer` - Read-only access

**Protected Endpoints**:
```python
from fastapi import Depends, HTTPException
from app.utils.dependencies import get_current_user

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    current_user: dict = Depends(get_current_user)
):
    # Check role
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(403, "Insufficient permissions")
    ...
```

==================================================
🧹 CODING STANDARDS
==================================================

**Python Best Practices**:
- Use type hints everywhere
- Add docstrings to all functions/classes
- Use environment variables (never hardcode secrets)
- Add comprehensive logging
- Implement proper exception handling
- Avoid global state
- Write production-ready code
- Keep functions small and focused (< 50 lines)

**Example Function**:
```python
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

async def process_csv_file(
    file_path: str, 
    file_id: str,
    user_id: Optional[str] = None
) -> List[dict]:
    """
    Process CSV file and convert rows to semantic chunks.
    
    Args:
        file_path: Path to CSV file
        file_id: Unique file identifier
        user_id: User who uploaded the file
        
    Returns:
        List of document chunks with embeddings
        
    Raises:
        ValueError: If file is invalid or empty
        IOError: If file cannot be read
    """
    try:
        logger.info(f"Processing CSV file: {file_path}")
        # Implementation
        ...
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        raise
```

==================================================
🚀 PERFORMANCE RULES
==================================================

**Optimization Strategies**:

1. **Avoid Rebuilding Vector Store**
   - Use incremental updates
   - Cache embeddings
   - Store vectors in MongoDB

2. **Efficient File Processing**
   - Stream large files
   - Process in chunks (pandas chunksize)
   - Use async I/O

3. **Query Optimization**
   - Cache frequent queries
   - Use database indexes
   - Limit result size

4. **Embedding Efficiency**
   - Batch embedding generation
   - Reuse model instances (singleton pattern)
   - Use GPU if available

5. **API Performance**
   - Implement caching (Redis)
   - Use connection pooling
   - Add request timeouts
   - Implement pagination

==================================================
🧪 TESTING REQUIREMENTS
==================================================

**Test Coverage**:
- Unit tests for all services (pytest)
- Integration tests for API endpoints
- Security tests (authentication, authorization)
- Performance tests for large files

**Test Structure**:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_upload_csv_file(client: AsyncClient, auth_headers: dict):
    """Test CSV file upload with valid authentication."""
    files = {"file": ("test.csv", b"name,age\nJohn,30", "text/csv")}
    response = await client.post(
        "/upload", 
        files=files, 
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "file_id" in response.json()
```

**Security Testing**:
- SQL/NoSQL injection prevention
- Path traversal protection
- File upload validation
- Token validation
- CORS security

==================================================
🐛 ERROR HANDLING
==================================================

**Structured Error Responses**:
```python
from fastapi import HTTPException

# Don't expose internal errors
try:
    result = process_file(file)
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise HTTPException(400, "Invalid file format")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(500, "Internal server error")
```

**Error Response Format**:
```json
{
    "detail": "Error message",
    "error_type": "ValidationError",
    "timestamp": "2026-05-28T10:30:00Z"
}
```

==================================================
📝 LOGGING RULES
==================================================

**Logging Levels**:
- DEBUG - Detailed diagnostic info
- INFO - General operational events
- WARNING - Potentially harmful situations
- ERROR - Error events
- CRITICAL - Critical failures

**Example**:
```python
import logging

logger = logging.getLogger(__name__)

# Good logging
logger.info(f"Processing file {filename} for user {user_id}")
logger.warning(f"Large file detected: {file_size} bytes")
logger.error(f"Failed to process file: {error}", exc_info=True)

# Don't log sensitive data
# Bad: logger.info(f"User password: {password}")
# Bad: logger.info(f"API key: {api_key}")
```

==================================================
🎯 GOAL
==================================================

Generate clean, scalable, production-ready backend code for a modern RAG system with:

✅ Secure authentication (Keycloak)
✅ Robust file processing (CSV/Excel/PDF)
✅ Efficient vector search (MongoDB/FAISS)
✅ High-quality RAG pipeline (LangChain/LangGraph)
✅ Comprehensive testing (pytest)
✅ Security best practices
✅ Performance optimization
✅ Clear documentation
✅ Maintainable code structure

Focus on code quality, security, and scalability suitable for production deployment.
