#!/bin/bash

# Test Runner Script for RAG Backend
# Run all unit tests with coverage and quality checks

set -e

echo "🧪 Running RAG Backend Test Suite"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

# Check if in backend directory
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}Error: Must run from backend directory${NC}"
    exit 1
fi

# Install test dependencies
echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
pip install -q pytest pytest-cov pytest-asyncio httpx || true

# Run unit tests
echo -e "${YELLOW}🧪 Running unit tests...${NC}"
python3 -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=70

# Run security checks
echo ""
echo -e "${YELLOW}🔒 Running security checks (Bandit)...${NC}"
pip install -q bandit || true
bandit -r app -f screen || true

# Run code quality checks
echo ""
echo -e "${YELLOW}📝 Running code quality checks (Flake8)...${NC}"
pip install -q flake8 || true
flake8 app --count --select=E9,F63,F7,F82 --show-source --statistics || true
flake8 app --count --max-complexity=10 --max-line-length=127 --statistics || true

echo ""
echo -e "${GREEN}✅ Test suite complete!${NC}"
echo ""
echo "📊 Coverage report: file://$(pwd)/htmlcov/index.html"
