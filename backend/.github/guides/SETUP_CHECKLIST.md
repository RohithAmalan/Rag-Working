# Setup Checklist - Verification Steps

Use this checklist to verify your MongoDB Atlas RAG setup is complete.

## ✅ Pre-Setup (Prerequisites)

- [ ] Python 3.11+ installed
- [ ] MongoDB Atlas account created (free tier)
- [ ] Groq API account created
- [ ] Node.js 16+ installed (for frontend)
- [ ] Git installed
- [ ] Terminal/Command line access

## ✅ Installation

- [ ] Backend repository cloned
- [ ] Frontend repository cloned
- [ ] Virtual environment created: `/Users/rohith/RAG/.venv`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] All Python modules compile without errors

## ✅ Configuration

- [ ] `.env` file created (copied from `.github/config/.env.example`)
- [ ] `MONGODB_URI` set in `.env`
- [ ] `GROQ_API_KEY` set in `.env`
- [ ] MongoDB cluster running in Atlas
- [ ] MongoDB cluster IP whitelist configured
- [ ] MongoDB Atlas connection tested

## ✅ Database Setup

- [ ] MongoDB database created: `rag_db`
- [ ] Collections auto-created by backend: `documents` and `chunks`
- [ ] Indexes created automatically on startup
- [ ] Vector search indexes created (manual in Atlas console)

## ✅ Verification

Run this command to verify installation:
```bash
cd /Users/rohith/RAG/backend
bash verify.sh
```

Check for:
- [ ] ✓ Python version OK
- [ ] ✓ All required files present
- [ ] ✓ MongoDB module imports
- [ ] ✓ Collections module imports
- [ ] ✓ Embedding service imports
- [ ] ✓ Vector service imports
- [ ] ✓ RAG service imports
- [ ] ✓ Main application imports
- [ ] ✓ Motor installed
- [ ] ✓ PyMongo installed
- [ ] ✓ Sentence-transformers installed
- [ ] ✓ LangChain installed
- [ ] ✓ FastAPI installed

## ✅ Backend Startup

- [ ] Backend starts without errors
- [ ] MongoDB connection successful message appears
- [ ] RAG service initialized message appears
- [ ] Vector store ready message appears
- [ ] Backend listening on http://0.0.0.0:8000

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting RAG application
INFO:     Connecting to MongoDB: mongodb+srv://...
INFO:     MongoDB connection successful
INFO:     Created indexes on documents collection
INFO:     Created vector search index on chunks collection
INFO:     RAG service initialized successfully
INFO:     Vector store ready: {'total_documents': 0, 'total_chunks': 0, ...}
```

## ✅ API Testing

### Health Check
```bash
curl http://localhost:8000/health
```
- [ ] Returns `{"status": "ok", "app": "..."}`

### Get Documents
```bash
curl http://localhost:8000/documents
```
- [ ] Returns valid JSON with stats
- [ ] `total_documents`: 0 (initially)
- [ ] `total_chunks`: 0 (initially)

### Upload Test File
```bash
# Create test file
echo "Name,Sales
John,1000" > test.csv

# Upload
curl -X POST http://localhost:8000/upload \
  -F "files=@test.csv"
```
- [ ] Returns success status
- [ ] `processed_files`: 1
- [ ] `total_chunks`: > 0

### Query Test
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is in the data?", "top_k": 5}'
```
- [ ] Returns JSON response
- [ ] `answer` field present
- [ ] `retrieved_chunks` array present
- [ ] `citations` array present

## ✅ Frontend Testing (Optional)

- [ ] Frontend starts: `npm run dev`
- [ ] Opens at http://localhost:5173
- [ ] Can access upload page
- [ ] Can access chat page
- [ ] Upload functionality works
- [ ] Chat functionality works

## ✅ MongoDB Testing

### Via MongoDB Atlas Console
- [ ] Log into MongoDB Atlas
- [ ] Select your cluster
- [ ] Browse Collections
- [ ] `documents` collection exists
- [ ] `chunks` collection exists
- [ ] Can see uploaded documents
- [ ] Can see chunks with embeddings

### Via Command Line
```bash
python -c "
import asyncio
from app.db.mongo import get_database

async def test():
    db = get_database()
    docs = await db.documents.count_documents({})
    chunks = await db.chunks.count_documents({})
    print(f'Documents: {docs}, Chunks: {chunks}')

asyncio.run(test())
"
```
- [ ] Returns document and chunk counts
- [ ] Numbers increase after uploads

## ✅ Documentation

- [ ] Read: [QUICK_START.md](../guides/QUICK_START.md)
- [ ] Read: [MongoDB Integration Guide](../mongodb/INTEGRATION.md)
- [ ] Read: [Architecture](../instructions/ARCHITECTURE.md)
- [ ] Bookmarked: [Commands Reference](COMMANDS.md)
- [ ] Bookmarked: [API Reference](../instructions/API_REFERENCE.md)

## ✅ Production Ready

- [ ] All tests pass
- [ ] No errors in logs
- [ ] Database backups configured
- [ ] Monitoring set up
- [ ] Error logging configured
- [ ] API rate limiting configured (if needed)
- [ ] CORS configured for frontend origin
- [ ] SSL/TLS enabled (if deployed)

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check MongoDB URI
grep MONGODB_URI .env

# Check if cluster is running
# Go to MongoDB Atlas -> Clusters

# Check Python version
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### MongoDB connection fails
```bash
# Verify connection string
# Verify IP whitelist in Atlas console
# Check firewall settings
# Test with connection string from Atlas

# Verify database exists
# Go to MongoDB Atlas -> Clusters -> Collections
```

### No chunks generated
```bash
# Check file format (CSV, XLSX, PDF)
# Ensure file is not empty
# Check file content

# Test chunking manually:
python -c "
from app.rag.chunking import chunk_pdf_texts
chunks = chunk_pdf_texts('test.pdf', ['test text'], 900, 120)
print(f'Chunks generated: {len(chunks)}')
"
```

### API returns errors
```bash
# Check backend logs
# Look at console output

# Test individual endpoints
curl http://localhost:8000/health

# Check .env variables
grep -E "MONGODB|GROQ" .env

# Verify database is accessible
# Go to MongoDB Atlas console
```

## 📊 Expected State After Setup

| Item | Initial | After Upload | After Query |
|------|---------|--------------|-------------|
| Documents | 0 | 1+ | 1+ |
| Chunks | 0 | 10+ | 10+ |
| Embeddings | 0 | Generated | Generated |
| Query Responses | N/A | Works | Working |

## 🎯 Next Steps After Setup

1. ✅ Verify all checkboxes above
2. 📚 Read full documentation:
   - [MongoDB Integration](../mongodb/INTEGRATION.md)
   - [Architecture](../instructions/ARCHITECTURE.md)
3. 🚀 Deploy to production (see [DEPLOYMENT.md](../workflows/DEPLOYMENT.md))
4. 📊 Set up monitoring and alerts
5. 🔒 Implement authentication and authorization

## 📞 Support

- Issues → Check [QUICK_START.md](QUICK_START.md)
- Commands → See [COMMANDS.md](COMMANDS.md)
- API → See [API_REFERENCE.md](../instructions/API_REFERENCE.md)
- MongoDB → See [MongoDB Integration](../mongodb/INTEGRATION.md)

---

**Last Updated**: December 10, 2024
**Version**: 1.0
