# RAG Application - Production Ready

Advanced Retrieval-Augmented Generation (RAG) system with LangGraph multi-agent workflow.

## 🚀 Quick Start

```bash
# 1. Set up environment
cp backend/.env.example .env
# Edit .env and add your GROQ_API_KEY

# 2. Start application
docker-compose up -d

# 3. Access
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

**Full instructions:** See [HOW_TO_RUN.md](HOW_TO_RUN.md)

## 📊 Features

- **Multi-Agent RAG Pipeline** - LangGraph Phase 3 workflow
- **Smart Data Handling** - CSV/Excel (primary), PDF (secondary)
- **Query Expansion** - 3 variations for better coverage  
- **Cross-Encoder Reranking** - 20-30% accuracy boost
- **Citation Generation** - Inline source attribution
- **Analytics Dashboard** - Interactive data visualization
- **MongoDB Vector Store** - Scalable vector search
- **Docker Deployment** - One-command production setup

## 🏗 Architecture

```
Backend:  FastAPI + LangGraph + MongoDB + FAISS
Frontend: React + Vite + Tailwind CSS
LLM:      Groq API (llama-3.1-70b-versatile)
Embeddings: all-MiniLM-L6-v2
```

## 📁 Project Structure

```
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── rag/      # RAG pipeline (LangGraph, chunking, generation)
│   │   ├── services/ # Business logic (vector search, file handling)
│   │   ├── routes/   # API endpoints
│   │   └── db/       # MongoDB collections
│   ├── tests/        # Unit tests
│   └── Dockerfile    # Backend container
├── frontend/          # React application
│   ├── src/
│   │   ├── pages/    # Dashboard, Analytics, Login
│   │   ├── components/  # Reusable UI components
│   │   └── services/ # API client
│   └── Dockerfile    # Frontend container
├── docs/archive/      # Old documentation (archived)
└── docker-compose.yml # Unified Docker config
```

## 🔧 Configuration

Environment variables in `.env`:

```env
# Required
GROQ_API_KEY=your_key_here

# Optional
MINIO_ENABLED=false              # Use local storage
LANGGRAPH_WORKFLOW_MODE=multi_agent  # Phase 3 workflow
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## 📚 Documentation

- **[HOW_TO_RUN.md](HOW_TO_RUN.md)** - Complete setup and usage guide
- **[BUG_FIXES_SUMMARY.md](BUG_FIXES_SUMMARY.md)** - Recent fixes and improvements
- **[AGENTS.md](AGENTS.md)** - Agent customization instructions
- **[docs/archive/](docs/archive/)** - Older documentation (archived)

## 🎯 Recent Improvements

✅ Fixed analytics dashboard MinIO error  
✅ Fixed PDF upload and querying  
✅ Improved answer generation quality  
✅ Consolidated Docker configuration  
✅ Disabled annoying auto-refresh  
✅ Fixed single-record vs list-all queries  
✅ Cleaned up file explorer  

## 🧪 Development

```bash
# Development mode (hot-reload)
docker-compose --profile dev up

# Run tests
cd backend
pytest

# View logs
docker-compose logs -f backend
```

## 📝 API Endpoints

- `POST /upload` - Upload CSV/Excel/PDF files
- `POST /query` - Ask questions (RAG pipeline)
- `GET /documents` - List uploaded files
- `GET /documents/analytics/{file}` - Get file analytics
- `GET /health` - Health check

**Full API docs:** http://localhost:8000/docs

## 📄 License

MIT License

---

**Need help?** Check [HOW_TO_RUN.md](HOW_TO_RUN.md) or run `docker-compose logs -f backend`
