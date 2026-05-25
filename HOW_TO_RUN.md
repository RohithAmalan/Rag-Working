# How to Run the RAG Application

## ✅ All Docker Files Are Now Consolidated!

Everything is in **one file**: `docker-compose.yml`

The old `docker-compose.dev.yml` has been archived to `docker-compose.dev.yml.bak`.

---

## 🚀 Quick Start

### Option 1: Production Mode (Recommended)
```bash
cd /Users/rohith/RAG
docker-compose up -d
```

This starts:
- MongoDB
- Redis
- MinIO
- Backend (optimized build, port 8000)
- Frontend (Nginx production, port 5173→80)

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (if enabled)

---

### Option 2: Development Mode (Hot Reload)
```bash
cd /Users/rohith/RAG
docker-compose --profile dev up
```

This starts:
- MongoDB
- Redis
- MinIO
- Backend-dev (hot-reload enabled, port 8000)
- Frontend-dev (Vite dev server, port 5173)

**Features:**
- Code changes auto-reload
- Source code mounted as volumes
- Better for active development

---

## 📋 Common Commands

### Start Services
```bash
# Production (background)
docker-compose up -d

# Development (with logs)
docker-compose --profile dev up

# Specific service only
docker-compose up -d mongodb redis
```

### Stop Services
```bash
# Stop all
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Rebuild After Code Changes
```bash
# Production
docker-compose build backend
docker-compose up -d backend

# Development (no rebuild needed - uses hot reload)
docker-compose --profile dev up
```

### Check Status
```bash
# List running containers
docker-compose ps

# Check health
curl http://localhost:8000/health

# Container stats (CPU, memory)
docker stats
```

---

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
lsof -ti :8000 | xargs kill -9

# Or change port in docker-compose.yml
```

### Backend Won't Start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - GROQ_API_KEY not set in .env
# - MongoDB not ready (wait 30s on first start)
# - Port 8000 already in use
```

### MinIO Error (Analytics Dashboard)
This is now fixed! MinIO is disabled by default (`MINIO_ENABLED=false`).
Files are stored locally in `backend/uploads/files/`.

### Reset Everything
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Remove old images
docker rmi $(docker images 'rag-*' -q)

# Start fresh
docker-compose up -d
```

---

## 📁 File Structure

```
/Users/rohith/RAG/
├── docker-compose.yml          # ✅ UNIFIED CONFIG (use this!)
├── docker-compose.dev.yml.bak  # Old dev file (archived)
├── .env                        # Environment variables
├── backend/
│   ├── Dockerfile             # Backend build config
│   └── app/                   # Python FastAPI code
└── frontend/
    ├── Dockerfile             # Production build
    ├── Dockerfile.dev         # Development build
    └── src/                   # React/Vite code
```

---

## 🎯 What Changed?

### Before
```bash
# Had to specify both files
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### After  
```bash
# Single file with profiles
docker-compose up              # Production
docker-compose --profile dev up  # Development
```

---

## 📝 Environment Variables

Make sure `.env` file has:

```env
# Required
GROQ_API_KEY=your_key_here
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=password123

# MinIO (disabled by default)
MINIO_ENABLED=false

# LangGraph
LANGGRAPH_WORKFLOW_MODE=multi_agent

# Embedding
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

## 🎉 All 4 Issues Fixed!

✅ Analytics Dashboard - No more MinIO errors
✅ PDF Upload & Querying - PDFs now work correctly
✅ Answer Generation - Improved quality with reranking
✅ Docker Files - All consolidated into one file!

---

## 📚 More Help

- Full Docker guide: [DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md)
- Technical fixes: [BUG_FIXES_SUMMARY.md](BUG_FIXES_SUMMARY.md)
- API documentation: http://localhost:8000/docs (after starting)

---

**Need help?** Check logs with `docker-compose logs -f backend`
