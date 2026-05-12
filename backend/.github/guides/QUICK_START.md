# Quick Start - MongoDB Atlas Vector Search RAG

## Prerequisites

1. Python 3.11+ with venv
2. MongoDB Atlas account (free tier OK)
3. Groq API key
4. Node.js 16+ (for frontend)

## Installation (5 minutes)

### 1. Backend Setup

```bash
cd /Users/rohith/RAG/backend

# Activate virtual environment
source /Users/rohith/RAG/.venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure MongoDB

```bash
# Copy example config
cp .github/config/.env.example .env

# Edit .env with your MongoDB Atlas URI
# Get from: https://cloud.mongodb.com -> Connect -> Connect to your application
```

**Example .env**:
```
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/?retryWrites=true&w=majority
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Start Backend

```bash
# From /Users/rohith/RAG/backend with venv activated
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting RAG application
INFO:     MongoDB connection established
INFO:     RAG service initialized successfully
INFO:     Vector store ready: {'total_documents': 0, 'total_chunks': 0, ...}
```

### 4. Start Frontend (optional)

```bash
cd /Users/rohith/RAG/frontend
npm run dev
```

Opens at: http://localhost:5173

## Upload Your First File

### Via cURL

```bash
# Upload a CSV file
curl -X POST http://localhost:8000/upload \
  -F "files=@example.csv"
```

### Via Frontend

1. Go to http://localhost:5173
2. Click "Upload Files"
3. Select CSV, XLSX, or PDF
4. Click "Upload"

## Query Your Data

### Via cURL

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total sales?", "top_k": 5}'
```

### Via Frontend

1. Click "Chat"
2. Type your question
3. Get instant AI-powered answers with citations

## Check Vector Store Status

```bash
curl http://localhost:8000/documents
```

Returns: Total documents, total chunks, and statistics.

## Verify MongoDB Connection

```bash
# Test in Python REPL
python
>>> from app.db.mongo import get_database
>>> print("✓ MongoDB connection working")
```

## Common Issues

### "MONGODB_URI not in .env"
- Copy `.github/config/.env.example` to `.env`
- Add your MongoDB Atlas connection string
- Restart backend

### "Failed to connect to MongoDB"
- Check MongoDB Atlas cluster is running
- Verify IP whitelist includes your IP: Atlas Console → Network Access
- Test connection string locally

### "No chunks generated"
- Ensure file is not empty
- Check file format (CSV, XLSX, PDF)
- Check backend logs for parsing errors

## Architecture Overview

```
┌─────────────┐
│  Frontend   │ (React + Vite)
│  (localhost:5173)
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  FastAPI Backend │ (localhost:8000)
├──────────────────┤
│  • Upload API    │
│  • Query API     │
│  • Documents API │
└──────┬───────────┘
       │
       ▼
┌──────────────────────────┐
│  Embedding Service       │
│  (sentence-transformers) │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  MongoDB Atlas Vector Store  │
├──────────────────────────────┤
│  • documents collection      │
│  • chunks collection         │
│  • Vector search indexes     │
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│  Groq LLM API            │
│  (llama-3.1-8b-instant)  │
└──────────────────────────┘
```

## File Types Supported

| Type | Format | Priority | Use Case |
|------|--------|----------|----------|
| CSV | `.csv` | Primary | Tabular business data |
| Excel | `.xlsx` | Primary | Spreadsheets |
| PDF | `.pdf` | Secondary | Documents, reports |

## Next Steps

1. [Read Full MongoDB Integration Guide](../mongodb/INTEGRATION.md)
2. Create MongoDB Atlas Vector Search index (see guide section 4)
3. Deploy to production with your domain
4. Set up continuous backup strategy

## Support

- Backend logs: Console output when running
- MongoDB Atlas console: https://cloud.mongodb.com
- API documentation: http://localhost:8000/docs (when running)
- See: [COMMANDS.md](COMMANDS.md) for more commands
