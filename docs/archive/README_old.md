# RAG System

Production-ready Retrieval-Augmented Generation (RAG) system with FastAPI backend and React frontend.

![Backend CI](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Backend%20CI/badge.svg)
![Frontend CI](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Frontend%20CI/badge.svg)
![Integration Test](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Full%20System%20Test/badge.svg)

## Features

- 🔐 **Authentication**: Simple login system with token-based auth
- 📊 **Multi-source RAG**: Support for CSV, Excel, and PDF files
- 🧠 **LangGraph Integration**: Advanced query routing with conditional logic
- 💾 **Dual Storage**: MongoDB Atlas for production, FAISS for local development
- 🎨 **Modern UI**: React + Vite with TailwindCSS
- 🔍 **Semantic Search**: Vector similarity search with embeddings
- 📈 **Analytics Dashboard**: Visualize your data with interactive charts
- ✅ **Tested**: Comprehensive test suite with >70% coverage

## Tech Stack

### Backend
- FastAPI
- LangGraph
- MongoDB Atlas / FAISS
- Groq API (LLM)
- Sentence Transformers (embeddings)
- MinIO (object storage)

### Frontend
- React 18
- Vite
- TailwindCSS
- React Router
- Recharts
- React Hot Toast

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Run server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pytest --cov=app --cov-report=term
```

## Authentication

Demo credentials:
- Username: `admin` / Password: `admin123`
- Username: `demo` / Password: `demo123`
- Username: `user` / Password: `user123`

## API Endpoints

### Authentication
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout
- `GET /auth/verify` - Verify token

### RAG Operations
- `POST /upload` - Upload files
- `POST /query` - Ask questions
- `GET /documents` - List documents
- `DELETE /documents/{filename}` - Delete document

### System
- `GET /health` - Health check
- `GET /storage/status` - Storage status

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest -v

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_auth_service.py
```

### Code Quality

```bash
# Linting
flake8 app

# Formatting
black app tests

# Import sorting
isort app tests
```

## CI/CD

GitHub Actions workflows:
- **Backend CI**: Runs tests on Python 3.10, 3.11, 3.12
- **Frontend CI**: Builds and lints on Node 18, 20
- **Integration Test**: Full system test with MongoDB

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License
