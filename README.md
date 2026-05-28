# RAG Application with Keycloak SSO

Production-ready Retrieval-Augmented Generation (RAG) system with enterprise SSO authentication, role-based access control, and multi-application architecture.

## 🎯 Overview

A comprehensive RAG ecosystem featuring:
- **RAG App** - Excel/CSV semantic search with natural language queries
- **HR App** - Employee management with role-based permissions
- **Finance App** - Expense management and approval workflow
- **Keycloak SSO** - Single sign-on across all applications

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ | Node.js 18+ | Docker & Docker Compose

### 1. Start Infrastructure
```bash
docker-compose up -d keycloak mongodb redis minio
```

### 2. Configure Keycloak
See [KEYCLOAK_SSO_SETUP.md](./KEYCLOAK_SSO_SETUP.md) for complete setup guide.

### 3. Run Applications
```bash
# Backend
cd backend && source ../.venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Demo Apps (optional)
./start-sso-apps.sh
```

## 📱 Access URLs

- **RAG App**: http://localhost:5173
- **HR App**: http://localhost:3001
- **Finance App**: http://localhost:3002
- **API Docs**: http://localhost:8000/docs
- **Keycloak**: http://localhost:8080

## 📂 Structure

```
RAG/
├── backend/         # FastAPI API
├── frontend/        # React UI
├── hr-app/          # HR Management
├── finance-app/     # Finance Management
├── docs/            # Documentation
│   ├── setup-guides/   # Setup instructions
│   └── archive/        # Legacy docs
└── keycloak/        # SSO config
```

## 🔑 Default Login

**Keycloak Admin**: admin / admin  
**Test User**: rohith / password (configure in Keycloak first)

## 📚 Documentation

- [**HOW_TO_RUN.md**](./HOW_TO_RUN.md) - Complete setup guide
- [**KEYCLOAK_SSO_SETUP.md**](./KEYCLOAK_SSO_SETUP.md) - SSO configuration
- [**TESTING_GUIDE.md**](./TESTING_GUIDE.md) - Testing instructions
- [**SSO_DEMO_APPS_SUMMARY.md**](./SSO_DEMO_APPS_SUMMARY.md) - Demo apps overview
- [**AGENTS.md**](./AGENTS.md) - Backend AI agent instructions
- [docs/setup-guides/](./docs/setup-guides/) - Additional guides

## 🛠 Tech Stack

**Backend**: FastAPI · LangChain · FAISS · MongoDB · MinIO · Groq  
**Frontend**: React 18 · Vite · Tailwind · Keycloak JS  
**Infrastructure**: Docker · Keycloak · MongoDB · Redis

## 🎯 Features

✅ Excel/CSV semantic search  
✅ Natural language queries with RAG  
✅ Enterprise SSO (Keycloak)  
✅ Role-based access control (RBAC)  
✅ Multi-app authentication  
✅ Vector similarity search  
✅ Citation tracking  
✅ Comprehensive unit testing  
✅ CodeQL security analysis  

## 🧪 Testing

```bash
cd backend
pytest tests/ -v --cov=app
```

See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for details.

## 🐛 Troubleshooting

**Keycloak**: `docker-compose restart keycloak`  
**MongoDB**: Check port 27017 with `lsof -i :27017`  
**SSO Issues**: Verify clients configured in Keycloak  
**Frontend timeout**: Check backend is running on port 8000

---

**For detailed setup instructions, see [HOW_TO_RUN.md](./HOW_TO_RUN.md)**
