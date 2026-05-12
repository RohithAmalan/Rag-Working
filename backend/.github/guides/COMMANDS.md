# Commands Reference - MongoDB Atlas RAG System

## 🚀 Startup Commands

### 1. Activate Virtual Environment
```bash
source /Users/rohith/RAG/.venv/bin/activate
```

### 2. Install Dependencies
```bash
cd /Users/rohith/RAG/backend
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .github/config/.env.example .env
# Edit .env and add MongoDB URI and API keys
```

### 4. Start Backend Server
```bash
cd /Users/rohith/RAG/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start Frontend Server
```bash
cd /Users/rohith/RAG/frontend
npm run dev
```

---

## 🧪 Testing Commands

### Health Check
```bash
curl http://localhost:8000/health
```

### List Documents
```bash
curl http://localhost:8000/documents | python -m json.tool
```

### Upload Single File
```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@/path/to/file.csv"
```

### Upload Multiple Files
```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@file1.csv" \
  -F "files=@file2.pdf" \
  -F "files=@file3.xlsx"
```

### Query Documents
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the total sales?", "top_k": 5}'
```

### Query with Pretty Output
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is the top performer?", "top_k": 3}' | python -m json.tool
```

---

## 🔍 Debugging Commands

### Verify Backend Imports
```bash
cd /Users/rohith/RAG/backend
source /Users/rohith/RAG/.venv/bin/activate
python -c "import app.main; print('✓ Backend imports OK')"
```

### Run Verification Script
```bash
cd /Users/rohith/RAG/backend
bash verify.sh
```

### Check Python Version
```bash
python --version
```

### List Installed Packages
```bash
pip list | grep -E "motor|pymongo|sentence-transformers|langchain|fastapi"
```

### Test MongoDB Connection
```bash
python -c "
from motor.motor_asyncio import AsyncIOMotorClient
client = AsyncIOMotorClient('your-mongodb-uri')
print('✓ MongoDB client created')
"
```

### Check Environment Variables
```bash
echo $MONGODB_URI
echo $GROQ_API_KEY
```

---

## 📊 Database Commands

### Access MongoDB Shell (from MongoDB Atlas Console)
```javascript
// List all databases
show databases

// Select RAG database
use rag_db

// List collections
show collections

// Count documents
db.documents.countDocuments()
db.chunks.countDocuments()

// View sample document
db.documents.findOne()

// View sample chunk
db.chunks.findOne()

// Search by source
db.chunks.find({source: "file.csv"}).count()
```

---

## 🛠 Maintenance Commands

### Clear All Data (WARNING: Irreversible)
```bash
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clear():
    client = AsyncIOMotorClient('your-mongodb-uri')
    db = client['rag_db']
    await db.drop_collection('documents')
    await db.drop_collection('chunks')
    print('✓ Collections cleared')

asyncio.run(clear())
"
```

### Backup MongoDB Data
```bash
# Using mongoexport (if MongoDB tools installed)
mongoexport --uri "mongodb+srv://user:pass@cluster.mongodb.net/rag_db" \
  --collection documents \
  --out documents.json

mongoexport --uri "mongodb+srv://user:pass@cluster.mongodb.net/rag_db" \
  --collection chunks \
  --out chunks.json
```

### Check Backend Logs
```bash
# Real-time logs (if running in foreground)
# Look at console output when server is running
```

---

## 📝 File Operations

### Create Test CSV
```bash
cat > test_data.csv << 'EOF'
Product,Sales,Month
Laptop,5000,March
Phone,3000,March
Tablet,2000,April
EOF
```

### Create Test Directory
```bash
mkdir -p /Users/rohith/RAG/backend/test_files
```

### Upload Test File
```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@test_data.csv"
```

---

## 🔐 Configuration Commands

### View Current Configuration
```bash
python -c "
from app.utils.config import settings
print(f'Database: {settings.database_name}')
print(f'Embedding Model: {settings.embedding_model}')
print(f'Chunk Size: {settings.chunk_size}')
print(f'Chunk Overlap: {settings.chunk_overlap}')
"
```

### Verify .env File
```bash
# Check if .env exists
ls -la .env

# View .env (mask sensitive data)
grep -v API_KEY .env

# Check specific variable
grep MONGODB_URI .env
```

---

## 📦 Dependency Management

### Update All Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Install Specific Package
```bash
pip install motor==3.7.1
pip install pymongo==4.17.0
pip install sentence-transformers==5.4.1
```

### Generate Requirements File
```bash
pip freeze > requirements-frozen.txt
```

### Check for Outdated Packages
```bash
pip list --outdated
```

---

## 🌐 Network/Connectivity

### Test MongoDB Connection
```bash
curl -X GET "mongodb+srv://user:pass@cluster.mongodb.net/test"
```

### Check Backend API Health
```bash
curl -v http://localhost:8000/health
```

### Test DNS Resolution
```bash
nslookup cluster.mongodb.net
```

### Check Port Status
```bash
lsof -i :8000  # Backend port
lsof -i :5173  # Frontend port
```

---

## 🧹 Cleanup Commands

### Remove Old Uploads (Keep Recent 100)
```bash
cd /Users/rohith/RAG/backend/app/uploads/files
ls -t | tail -n +101 | xargs rm -f
```

### Clear Python Cache
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Clean Node Modules
```bash
cd /Users/rohith/RAG/frontend
rm -rf node_modules
npm install
```

---

## 📊 Performance Monitoring

### Monitor Active Connections
```bash
lsof | grep -E "mongo|uvicorn"
```

### Check Memory Usage (Backend)
```bash
ps aux | grep uvicorn
ps aux | grep node
```

### Monitor Network Traffic
```bash
netstat -an | grep :8000
netstat -an | grep :5173
```

### Profile Embedding Generation
```bash
python -c "
import time
from app.services.embedding_service import generate_single_embedding

start = time.time()
emb = generate_single_embedding('test text')
end = time.time()

print(f'Embedding generated in {(end-start)*1000:.2f}ms')
print(f'Dimension: {len(emb)}')
"
```

---

## 🚨 Emergency/Recovery

### Kill Backend Server
```bash
pkill -f uvicorn

# Or find and kill specific process
ps aux | grep uvicorn
kill -9 PID
```

### Kill Frontend Server
```bash
pkill -f "node.*vite"
pkill -f "npm.*dev"
```

### Force Restart Everything
```bash
# Kill all
pkill -f uvicorn
pkill -f "npm.*dev"
pkill -f "node.*"

# Wait
sleep 2

# Restart backend (in one terminal)
cd /Users/rohith/RAG/backend
source /Users/rohith/RAG/.venv/bin/activate
python -m uvicorn app.main:app --reload

# Restart frontend (in another terminal)
cd /Users/rohith/RAG/frontend
npm run dev
```

---

## 🎯 Common Workflows

### Workflow 1: Development Setup
```bash
cd /Users/rohith/RAG/backend
source /Users/rohith/RAG/.venv/bin/activate
cp .github/config/.env.example .env
# Edit .env
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Workflow 2: Test File Upload
```bash
# Create test file
echo "Name,Sales
John,1000
Jane,2000" > test.csv

# Upload
curl -X POST http://localhost:8000/upload -F "files=@test.csv"

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who has more sales?", "top_k": 5}'
```

### Workflow 3: Production Deployment
```bash
# Verify setup
bash verify.sh

# Create optimized build
npm run build

# Run with production settings
ENVIRONMENT=production python -m uvicorn app.main:app --workers 4
```

---

## ℹ️ Useful Information

### Default Ports
- Backend: 8000
- Frontend: 5173
- MongoDB: 27017 (Atlas only, cloud-hosted)

### Default Paths
- Backend: `/Users/rohith/RAG/backend`
- Frontend: `/Users/rohith/RAG/frontend`
- Uploads: `/Users/rohith/RAG/backend/app/uploads/files`
- Venv: `/Users/rohith/RAG/.venv`

### Key Environment Variables
```
MONGODB_URI              # MongoDB connection string
GROQ_API_KEY            # Groq API key
OPENAI_API_KEY          # OpenAI API key (optional)
EMBEDDING_MODEL         # Embedding model name
CHUNK_SIZE              # Document chunk size
CHUNK_OVERLAP           # Chunk overlap amount
```

### Embedding Model Info
- Model: all-MiniLM-L6-v2
- Dimension: 384
- Size: ~80MB
- Speed: ~100ms per chunk

---

## 🔗 Resources

- MongoDB Atlas: https://cloud.mongodb.com
- Groq Console: https://console.groq.com
- FastAPI Docs: https://fastapi.tiangolo.com
- Motor Docs: https://motor.readthedocs.io
- Sentence Transformers: https://www.sbert.net

---

**Last Updated**: December 10, 2024
**Version**: 1.0
