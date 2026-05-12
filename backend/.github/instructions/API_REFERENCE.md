# API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required. For production, implement:
- API Key authentication
- JWT tokens
- OAuth 2.0

## Response Format

All responses are JSON formatted:

```json
{
  "status": "success|error",
  "data": {},
  "error": null,
  "timestamp": "2024-12-10T10:30:00Z"
}
```

## Endpoints

---

## 1. Upload Files

**Endpoint**: `POST /upload`

**Description**: Upload and process files (CSV, XLSX, PDF) for indexing.

**Request**:
```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@report.pdf" \
  -F "files=@data.csv" \
  -F "files=@spreadsheet.xlsx"
```

**Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| files | File[] | Yes | One or more files to upload |

**Supported File Types**:
- `.csv` - Comma-separated values
- `.xlsx` - Excel spreadsheets
- `.pdf` - PDF documents

**Response (Success - 200)**:
```json
{
  "status": "success",
  "message": "Files uploaded and indexed successfully",
  "processed_files": 2,
  "total_chunks": 150,
  "documents": [
    {
      "filename": "report.pdf",
      "file_type": "pdf",
      "chunks": 47,
      "uploaded_at": "2024-12-10T10:30:00Z"
    },
    {
      "filename": "data.csv",
      "file_type": "csv",
      "chunks": 103,
      "uploaded_at": "2024-12-10T10:30:05Z"
    }
  ],
  "errors": []
}
```

**Response (Partial Failure - 207)**:
```json
{
  "status": "partial",
  "message": "Some files processed successfully",
  "processed_files": 1,
  "total_chunks": 47,
  "documents": [
    {
      "filename": "report.pdf",
      "file_type": "pdf",
      "chunks": 47,
      "status": "success"
    }
  ],
  "errors": [
    {
      "filename": "corrupted.csv",
      "error": "Invalid CSV format: missing delimiter"
    }
  ]
}
```

**Response (Error - 400)**:
```json
{
  "status": "error",
  "message": "No files provided or invalid file types",
  "error": "BadRequest",
  "details": "Accepted formats: .csv, .xlsx, .pdf"
}
```

**Status Codes**:
- `200` - All files uploaded successfully
- `207` - Some files uploaded, some failed
- `400` - No valid files or unsupported format
- `413` - File too large
- `500` - Server error during processing

**Notes**:
- Maximum file size: 100 MB per file
- Files are saved to `app/uploads/files/`
- Processed data is stored in MongoDB

---

## 2. Query Documents

**Endpoint**: `POST /query`

**Description**: Search documents and get AI-powered answers using LLM.

**Request**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What were the sales figures in Q3?",
    "top_k": 5
  }'
```

**Request Body (JSON)**:
```json
{
  "question": "What were the sales figures in Q3?",
  "top_k": 5
}
```

**Request Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| question | String | Yes | - | The user's question |
| top_k | Integer | No | 5 | Number of context chunks to retrieve (1-50) |

**Response (Success - 200)**:
```json
{
  "status": "success",
  "answer": "Based on the sales report, Q3 sales were $2.5M, with the largest contribution coming from laptop sales at $1.2M.",
  "retrieved_chunks": [
    {
      "_id": "65a1b2c3d4e5f6g7h8i9j0k2",
      "chunk_text": "Q3 sales summary: Total sales $2.5M, broken down as follows: Laptop $1.2M, Desktop $0.8M, Tablet $0.5M",
      "source": "sales_report.csv",
      "similarity_score": 0.92,
      "metadata": {
        "file_type": "csv",
        "source_priority": "primary"
      }
    },
    {
      "_id": "65a1b2c3d4e5f6g7h8i9j0k3",
      "chunk_text": "Sales were strong in March (Q1), April (Q2), and July-September (Q3). Q3 was our best quarter.",
      "source": "annual_report.pdf",
      "similarity_score": 0.78,
      "metadata": {
        "file_type": "pdf",
        "source_priority": "secondary"
      }
    }
  ],
  "citations": [
    "sales_report.csv",
    "annual_report.pdf"
  ],
  "timestamp": "2024-12-10T10:30:00Z"
}
```

**Response (No Results - 200)**:
```json
{
  "status": "success",
  "answer": "I don't have information about that in the provided documents.",
  "retrieved_chunks": [],
  "citations": [],
  "timestamp": "2024-12-10T10:30:00Z"
}
```

**Response (Error - 400)**:
```json
{
  "status": "error",
  "message": "Invalid query parameters",
  "error": "BadRequest",
  "details": "Question cannot be empty"
}
```

**Response (Error - 500)**:
```json
{
  "status": "error",
  "message": "Failed to process query",
  "error": "InternalServerError",
  "details": "MongoDB connection failed"
}
```

**Status Codes**:
- `200` - Query processed successfully
- `400` - Invalid parameters (empty question, invalid top_k)
- `404` - No documents uploaded
- `500` - Server error

**Notes**:
- Question is converted to embedding (384-dimensional)
- Vector search retrieves `top_k` most similar chunks
- Primary sources (CSV/XLSX) are prioritized
- LLM generates answer from retrieved context
- Similarity scores range from 0 to 1

---

## 3. List Documents

**Endpoint**: `GET /documents`

**Description**: List all uploaded documents and statistics.

**Request**:
```bash
curl http://localhost:8000/documents
```

**Response (Success - 200)**:
```json
{
  "status": "success",
  "total_chunks": 1250,
  "total_documents": 5,
  "documents": [
    {
      "_id": "65a1b2c3d4e5f6g7h8i9j0k1",
      "filename": "sales_report.csv",
      "file_type": "csv",
      "chunks": 150,
      "uploaded_at": "2024-12-10T10:00:00Z"
    },
    {
      "_id": "65a1b2c3d4e5f6g7h8i9j0k4",
      "filename": "annual_report.pdf",
      "file_type": "pdf",
      "chunks": 75,
      "uploaded_at": "2024-12-10T09:45:00Z"
    }
  ],
  "stats": {
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "total_embeddings": 1250,
    "storage_size_mb": 1.92
  },
  "breakdown_by_type": {
    "csv": {
      "count": 2,
      "chunks": 350
    },
    "xlsx": {
      "count": 1,
      "chunks": 450
    },
    "pdf": {
      "count": 2,
      "chunks": 450
    }
  },
  "timestamp": "2024-12-10T10:30:00Z"
}
```

**Response (No Documents - 200)**:
```json
{
  "status": "success",
  "total_chunks": 0,
  "total_documents": 0,
  "documents": [],
  "stats": {
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "total_embeddings": 0,
    "storage_size_mb": 0
  },
  "breakdown_by_type": {},
  "timestamp": "2024-12-10T10:30:00Z"
}
```

**Status Codes**:
- `200` - Retrieved successfully
- `500` - Server error

**Notes**:
- Returns all documents regardless of source priority
- Statistics include total chunks and storage estimate
- Storage size is approximate (1.5KB per embedding + metadata)

---

## 4. Delete Document

**Endpoint**: `DELETE /documents/{document_id}`

**Description**: Delete a specific document and all its chunks.

**Request**:
```bash
curl -X DELETE http://localhost:8000/documents/65a1b2c3d4e5f6g7h8i9j0k1
```

**Response (Success - 200)**:
```json
{
  "status": "success",
  "message": "Document deleted successfully",
  "document_id": "65a1b2c3d4e5f6g7h8i9j0k1",
  "chunks_deleted": 150,
  "timestamp": "2024-12-10T10:30:00Z"
}
```

**Response (Not Found - 404)**:
```json
{
  "status": "error",
  "message": "Document not found",
  "error": "NotFound",
  "document_id": "invalid_id"
}
```

**Status Codes**:
- `200` - Deleted successfully
- `404` - Document not found
- `500` - Server error

---

## 5. Health Check

**Endpoint**: `GET /health`

**Description**: Check backend and MongoDB connection status.

**Request**:
```bash
curl http://localhost:8000/health
```

**Response (Healthy - 200)**:
```json
{
  "status": "healthy",
  "backend": "running",
  "database": "connected",
  "services": {
    "embedding": "ready",
    "vector_search": "ready",
    "llm": "ready"
  },
  "timestamp": "2024-12-10T10:30:00Z"
}
```

**Response (Degraded - 503)**:
```json
{
  "status": "degraded",
  "backend": "running",
  "database": "disconnected",
  "services": {
    "embedding": "ready",
    "vector_search": "unavailable",
    "llm": "ready"
  },
  "error": "MongoDB connection timeout"
}
```

**Status Codes**:
- `200` - All systems healthy
- `503` - Some systems unavailable

---

## Error Responses

### Standard Error Format

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error": "ErrorType",
  "details": "Additional error details",
  "timestamp": "2024-12-10T10:30:00Z"
}
```

### Common Errors

| Error | Status | Cause | Solution |
|-------|--------|-------|----------|
| `BadRequest` | 400 | Invalid parameters | Check query parameters |
| `NotFound` | 404 | Resource doesn't exist | Verify document/resource ID |
| `Conflict` | 409 | Duplicate file upload | Use different filename |
| `PayloadTooLarge` | 413 | File exceeds size limit | Upload smaller file |
| `InternalServerError` | 500 | Server error | Check backend logs |
| `ServiceUnavailable` | 503 | Database unavailable | Verify MongoDB connection |

---

## Rate Limiting

Currently not implemented. For production, implement:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1702209000
```

Recommendation: 1000 requests per hour per IP

---

## Pagination (Future)

For endpoints returning large result sets:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 250,
    "total_pages": 25
  }
}
```

---

## Examples

### Example 1: Complete Upload and Query Flow

```bash
# 1. Upload files
curl -X POST http://localhost:8000/upload \
  -F "files=@data.csv"

# Response shows data.csv uploaded with 100 chunks

# 2. Query the data
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What was the highest sales value?",
    "top_k": 3
  }'

# Response shows answer from LLM with retrieved chunks
```

### Example 2: Using Python Requests

```python
import requests

# Upload
files = {'files': open('data.csv', 'rb')}
response = requests.post('http://localhost:8000/upload', files=files)
print(response.json())

# Query
query = {
    "question": "What was the highest sales value?",
    "top_k": 5
}
response = requests.post('http://localhost:8000/query', json=query)
print(response.json())
```

### Example 3: Using JavaScript/Fetch

```javascript
// Upload
const formData = new FormData();
formData.append('files', fileInput.files[0]);

const uploadRes = await fetch('http://localhost:8000/upload', {
  method: 'POST',
  body: formData
});
const uploadData = await uploadRes.json();

// Query
const queryRes = await fetch('http://localhost:8000/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: 'What was the highest sales value?',
    top_k: 5
  })
});
const queryData = await queryRes.json();
```

---

## Timeout

- **Upload**: 5 minutes (for large files)
- **Query**: 30 seconds
- **List Documents**: 10 seconds

---

**Last Updated**: December 10, 2024
