# Bug Fixes Summary - Docker Production Deployment

## Date
January 2025

## Issues Fixed

### 1. Analytics Dashboard - MinIO Error ✅

**Problem:**
- Analytics dashboard showed "Failed to download file from MinIO" error
- User had `MINIO_ENABLED=false` in `.env`, but files were being deleted after upload
- Analytics/preview endpoints tried to read from `doc.get("path")` but files no longer existed

**Root Cause:**
- In `backend/app/services/rag_service.py`, uploaded files were deleted after processing regardless of MinIO status
- When MinIO is disabled, files are stored locally at `backend/uploads/files/`
- But the cleanup logic deleted them unconditionally

**Fix:**
Modified `backend/app/services/rag_service.py` lines 127-144:
- Only delete local files when MinIO is enabled (files are backed up to S3)
- When MinIO is disabled, keep local files for analytics/preview functionality
- Added conditional logic checking `storage_backend == "minio"` before deleting

**Files Modified:**
- `backend/app/services/rag_service.py`

---

### 2. PDF Upload and Querying ✅

**Problem:**
- User reported: "if i upload pdf and ask means its not working"
- PDFs were being uploaded and chunked correctly but not retrieved during queries

**Root Cause:**
- In `backend/app/rag/langgraph_nodes.py` (retrieve_node), retrieval was hardcoded to `source_priority="primary"`
- PDFs have `source_priority="secondary"` (defined in chunking.py)
- This meant PDF chunks were never being retrieved in the LangGraph workflow

**Fix:**
Modified `backend/app/rag/langgraph_nodes.py` lines 103-136:
- Added logic to retrieve primary sources first
- If not enough primary results and no strong exact match, add secondary sources (PDFs)
- Mirrors the behavior in `backend/app/services/rag_service.py` (search_and_retrieve method)
- Logs when secondary chunks are added

**Files Modified:**
- `backend/app/rag/langgraph_nodes.py`

---

### 3. Answer Generation Quality ✅

**Problem:**
- User reported: "generating answers not coming correctly"
- Answers may have been incomplete or missing relevant chunks

**Root Cause:**
- In `backend/app/rag/langgraph_nodes.py` line 144, reranker was using wrong variable
- Code retrieved `all_chunks` from query expansion but passed `chunks` (undefined/old) to reranker
- This caused reranking to fail or use stale data

**Fix:**
Modified `backend/app/rag/langgraph_nodes.py` lines 138-158:
- Changed `reranker.rerank(chunks=chunks)` to `reranker.rerank(chunks=all_chunks)`
- Updated all references from `chunks` to `all_chunks` in strategy determination and logging
- Ensures reranker processes the correct merged chunks from query expansion

**Files Modified:**
- `backend/app/rag/langgraph_nodes.py`

---

### 4. Docker File Consolidation ✅

**Problem:**
- User requested: "make the docker file to set in one file"
- Had two separate files: `docker-compose.yml` and `docker-compose.dev.yml`
- Required using `-f` flags: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`

**Solution:**
Consolidated into a single `docker-compose.yml` using Docker Compose profiles:

**Changes:**
1. Added profile-based services:
   - `backend` (profiles: `[prod, default]`) - Production build
   - `backend-dev` (profiles: `[dev]`) - Development with hot-reload
   - `frontend` (profiles: `[prod, default]`) - Production Nginx serving
   - `frontend-dev` (profiles: `[dev]`) - Vite dev server with hot-reload

2. Usage:
   - Production: `docker-compose up` (default profile)
   - Development: `docker-compose --profile dev up`

3. Created `DOCKER_COMPOSE_GUIDE.md` with:
   - Usage instructions
   - Migration notes
   - Common commands
   - Benefits explanation

**Files Modified:**
- `docker-compose.yml` (complete rewrite with profiles)

**Files Created:**
- `DOCKER_COMPOSE_GUIDE.md`

**Files Deprecated:**
- `docker-compose.dev.yml` (can be deleted)

---

## Testing Recommendations

### 1. Analytics Dashboard
1. Upload a CSV/Excel file (with MinIO disabled)
2. Navigate to Analytics Dashboard
3. Select the uploaded file
4. Verify charts and statistics display correctly
5. Check that file preview works

### 2. PDF Querying
1. Upload a PDF file
2. Ask a question related to PDF content
3. Verify PDF chunks are retrieved (check backend logs for "Added X secondary chunks")
4. Verify answer includes PDF content

### 3. Answer Quality
1. Ask complex queries requiring multiple chunks
2. Ask queries that should retrieve from both CSV and PDF
3. Verify answers are coherent and well-formatted
4. Check that top reranked chunks are used (logs show rerank scores)

### 4. Docker Consolidation
```bash
# Test production mode
docker-compose down
docker-compose up -d
docker-compose ps  # Should show backend, frontend (not -dev variants)
curl http://localhost:8000/health

# Test development mode
docker-compose down
docker-compose --profile dev up -d
docker-compose ps  # Should show backend-dev, frontend-dev
# Edit backend/app/main.py and verify auto-reload
curl http://localhost:8000/health
```

---

## Deployment Steps

1. **Backup existing data** (if MinIO was previously enabled)
   ```bash
   docker-compose exec mongodb mongodump
   ```

2. **Pull latest code**
   ```bash
   git pull origin main
   ```

3. **Rebuild containers**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   ```

4. **Start services**
   ```bash
   # Production
   docker-compose up -d
   
   # Or development
   docker-compose --profile dev up -d
   ```

5. **Verify health**
   ```bash
   docker-compose ps
   docker-compose logs -f backend
   curl http://localhost:8000/health
   ```

6. **Test uploads** (re-upload test files to recreate local storage)

---

## Configuration Checklist

Ensure `.env` file has:
```env
# Required
GROQ_API_KEY=your_key_here
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=password123

# MinIO (set to false for local storage)
MINIO_ENABLED=false

# LangGraph (multi-agent workflow)
LANGGRAPH_WORKFLOW_MODE=multi_agent

# Embedding
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

---

## Performance Notes

- **Local file storage** (MinIO disabled): Files kept in `backend/uploads/files/`
- **Docker volumes**: `backend_uploads` and `backend_vectorstore` persist across restarts
- **Query expansion**: Retrieves from 3 query variations for better coverage
- **Reranking**: Cross-encoder reranks top candidates for accuracy
- **Hybrid search**: Combines exact match, keyword search, and vector similarity

---

## Rollback Plan

If issues occur:
```bash
# Stop services
docker-compose down

# Restore MongoDB backup
docker-compose up -d mongodb
docker-compose exec mongodb mongorestore /backup

# Use previous docker-compose files
git checkout HEAD~1 docker-compose.yml docker-compose.dev.yml
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---

## Future Improvements

1. Add MongoDB Atlas Vector Search index for better performance
2. Implement incremental updates (avoid re-embedding on analytics refresh)
3. Add file versioning support
4. Implement user file quotas
5. Add batch upload endpoint
6. Cache analytics results in Redis

---

## Contact

For issues or questions, check:
- Backend logs: `docker-compose logs -f backend`
- MongoDB status: `docker-compose exec mongodb mongosh`
- Health endpoint: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
