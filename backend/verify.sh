#!/bin/bash
# MongoDB Atlas Vector Search Integration Verification Script

set -e

echo "================================"
echo "RAG System Verification Script"
echo "================================"
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -n "✓ Checking Python version... "
PYTHON_VERSION=$(python --version 2>&1)
echo $PYTHON_VERSION

# Activate venv
echo -n "✓ Activating virtual environment... "
source /Users/rohith/RAG/.venv/bin/activate
echo "OK"
echo

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}✗ Error: requirements.txt not found${NC}"
    echo "  Please run this script from /Users/rohith/RAG/backend"
    exit 1
fi

# Check all required files exist
echo "Checking required files..."
required_files=(
    "app/db/mongo.py"
    "app/db/collections.py"
    "app/services/embedding_service.py"
    "app/services/mongo_vector_service.py"
    "app/services/rag_service.py"
    "app/routes/rag_routes.py"
    "app/main.py"
    ".env.example"
    "requirements.txt"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file (MISSING)"
        exit 1
    fi
done
echo

# Test Python imports
echo "Testing Python imports..."
python -c "from app.db.mongo import connect_to_mongo, get_database" && echo -e "${GREEN}✓${NC} MongoDB module" || echo -e "${RED}✗${NC} MongoDB module"
python -c "from app.db.collections import DocumentsCollection, ChunksCollection" && echo -e "${GREEN}✓${NC} Collections module" || echo -e "${RED}✗${NC} Collections module"
python -c "from app.services.embedding_service import generate_embeddings" && echo -e "${GREEN}✓${NC} Embedding service" || echo -e "${RED}✗${NC} Embedding service"
python -c "from app.services.mongo_vector_service import MongoVectorService" && echo -e "${GREEN}✓${NC} Vector service" || echo -e "${RED}✗${NC} Vector service"
python -c "from app.services.rag_service import RagService" && echo -e "${GREEN}✓${NC} RAG service" || echo -e "${RED}✗${NC} RAG service"
python -c "import app.main" && echo -e "${GREEN}✓${NC} Main application" || echo -e "${RED}✗${NC} Main application"
echo

# Check dependencies
echo "Checking key dependencies..."
python -c "import motor; print('Motor:', motor.__version__)" 2>/dev/null && echo -e "${GREEN}✓${NC} motor" || echo -e "${YELLOW}⚠${NC} motor (not installed)"
python -c "import pymongo; print('PyMongo:', pymongo.__version__)" 2>/dev/null && echo -e "${GREEN}✓${NC} pymongo" || echo -e "${YELLOW}⚠${NC} pymongo"
python -c "import sentence_transformers; print('Sentence-Transformers: OK')" 2>/dev/null && echo -e "${GREEN}✓${NC} sentence-transformers" || echo -e "${YELLOW}⚠${NC} sentence-transformers"
python -c "import langchain; print('LangChain: OK')" 2>/dev/null && echo -e "${GREEN}✓${NC} langchain" || echo -e "${YELLOW}⚠${NC} langchain"
python -c "import fastapi; print('FastAPI: OK')" 2>/dev/null && echo -e "${GREEN}✓${NC} fastapi" || echo -e "${RED}✗${NC} fastapi"
echo

# Check configuration
echo "Checking configuration..."
if [ -f ".env" ]; then
    if grep -q "MONGODB_URI" .env; then
        echo -e "${GREEN}✓${NC} .env exists with MONGODB_URI"
    else
        echo -e "${YELLOW}⚠${NC} .env exists but no MONGODB_URI set"
    fi
else
    echo -e "${YELLOW}⚠${NC} .env not found (copy from .env.example)"
fi
echo

echo "================================"
echo -e "${GREEN}Verification Complete!${NC}"
echo "================================"
echo
echo "Next steps:"
echo "1. Copy .env.example to .env: cp .env.example .env"
echo "2. Add MongoDB URI to .env: MONGODB_URI=mongodb+srv://..."
echo "3. Add Groq API key to .env: GROQ_API_KEY=..."
echo "4. Start backend: python -m uvicorn app.main:app --reload"
echo
echo "Documentation:"
echo "  - Full guide: ./MONGODB_INTEGRATION.md"
echo "  - Quick start: ./QUICK_START.md"
echo "  - Implementation: ./IMPLEMENTATION_SUMMARY.md"
echo
