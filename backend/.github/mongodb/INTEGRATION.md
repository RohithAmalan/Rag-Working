# MongoDB Atlas Vector Search Integration

## Overview

This RAG system integrates with **MongoDB Atlas Vector Search** for scalable, cloud-based vector storage and semantic retrieval. This replaces the local FAISS vector store with a production-grade database.

## Architecture

### Before (FAISS)
```
Upload → Chunk → Embed → FAISS Index (in-memory) → Query → Retrieve
```

### After (MongoDB Atlas Vector Search)
```
Upload → Chunk → Embed → MongoDB Vector Index → Query → Retrieve via Aggregation Pipeline
```

## Tech Stack

- **Vector Database**: MongoDB Atlas (Cloud)
- **Async Driver**: Motor (asyncio-compatible)
- **Embedding Model**: Sentence-Transformers (all-MiniLM-L6-v2 by default)
- **LLM**: Groq API (llama-3.1-8b-instant)
- **Backend**: FastAPI + Uvicorn

## Setup Instructions

### 1. Create MongoDB Atlas Account

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Sign up or log in
3. Create a new project
4. Create a new cluster (M0 free tier is sufficient for development)

### 2. Get Connection String

1. In MongoDB Atlas, click "Connect"
2. Select "Connect to your application"
3. Copy your connection string (looks like):
   ```
   mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

### 3. Configure Environment Variables

1. Copy `.github/config/.env.example` to `.env`
2. Fill in your MongoDB URI:
   ```bash
   MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"
   ```
3. Set other variables (API keys, etc.)

### 4. Start Backend with MongoDB

```bash
cd /Users/rohith/RAG/backend
source /Users/rohith/RAG/.venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Important**: On first startup, the backend will:
- Connect to MongoDB
- Create collections: `documents` and `chunks`
- Create vector search indexes (if not using Atlas Search, basic indexes are created)

## MongoDB Collections

See [SCHEMA.md](SCHEMA.md) for detailed collection schemas.

## Vector Search Configuration

See [VECTOR_SEARCH.md](VECTOR_SEARCH.md) for detailed vector search setup.

## Key Features

### 1. Source Prioritization
- **Primary sources** (CSV/XLSX): Business data retrieved first
- **Secondary sources** (PDF): Supporting documents if primary results insufficient

### 2. Batch Operations
- Chunks inserted in batches for efficiency
- Embeddings generated using batch encoding

### 3. Async Architecture
- Non-blocking database operations
- Motor driver for async MongoDB access
- FastAPI async routes

### 4. Error Handling
- Graceful degradation if MongoDB unavailable
- Detailed error logs for debugging
- Type hints for IDE support

## API Usage

### 1. Upload Files

```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@report.pdf" \
  -F "files=@data.csv"
```

Response:
```json
{
  "message": "Files uploaded and indexed successfully",
  "processed_files": 2,
  "total_chunks": 150,
  "documents": [...],
  "errors": []
}
```

### 2. Query Documents

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What were the sales in Q3?", "top_k": 5}'
```

Response:
```json
{
  "answer": "Sales in Q3 were $2.5M...",
  "retrieved_chunks": [
    {
      "content": "Q3 sales summary...",
      "score": 0.89,
      "metadata": {}
    }
  ],
  "citations": [...]
}
```

### 3. List Documents

```bash
curl http://localhost:8000/documents
```

Response:
```json
{
  "total_chunks": 1250,
  "total_documents": 5,
  "documents": [...],
  "stats": {
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dimension": 384
  }
}
```

## Code Structure

```
app/
├── db/
│   ├── mongo.py           # Connection lifecycle
│   └── collections.py     # Collection managers
├── services/
│   ├── embedding_service.py        # Embedding generation
│   ├── mongo_vector_service.py     # Vector operations
│   ├── rag_service.py              # Orchestration
│   └── file_service.py             # File processing
├── routes/
│   └── rag_routes.py               # API endpoints
└── main.py                         # FastAPI app + startup
```

## Performance Tips

1. **Batch Size**: Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` in `.env`
2. **Embedding Model**: Use lighter models like `MiniLM` for speed
3. **Vector Search**: MongoDB Atlas automatically optimizes indexes
4. **Caching**: Enable MongoDB Atlas caching for frequently accessed data
5. **Sharding**: For large datasets, enable sharding on `document_id`

## Troubleshooting

### MongoDB Connection Failed
```bash
# Check MONGODB_URI in .env
# Verify network access in MongoDB Atlas (IP whitelist)
# Test connection:
python -c "from motor.motor_asyncio import AsyncIOMotorClient; print('Motor installed correctly')"
```

### Vector Search Index Not Created
```bash
# Manually create in MongoDB Atlas Console
# Or modify app/db/mongo.py to create indexes with fallback logic
```

### Slow Queries
1. Check if vector search index is created in MongoDB Atlas
2. Monitor query performance in Atlas console
3. Increase `top_k` limit gradually to find sweet spot
4. Verify embedding model is being cached properly

### Memory Issues
- Embeddings are generated on-demand (not cached)
- Use smaller batch sizes in `generate_batch_embeddings()`
- Monitor MongoDB memory usage in Atlas console

## Next Steps

1. ✅ Basic setup complete
2. Set up MongoDB Atlas Vector Search index (see [VECTOR_SEARCH.md](VECTOR_SEARCH.md))
3. Upload test files via the API
4. Monitor queries in MongoDB Atlas console
5. Optimize embeddings and search parameters
6. Deploy to production with SSL/TLS

## References

- [MongoDB Atlas Documentation](https://docs.mongodb.com/manual/atlas/)
- [Motor Documentation](https://motor.readthedocs.io/)
- [Sentence-Transformers](https://www.sbert.net/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vector Search Documentation](https://www.mongodb.com/docs/atlas/atlas-vector-search/overview/)

---

**Last Updated**: December 10, 2024
