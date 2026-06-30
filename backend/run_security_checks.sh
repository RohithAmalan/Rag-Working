#!/bin/bash

# Security and Vulnerability Checks Script
# This script runs comprehensive security checks on the backend code

set -e

echo "=========================================="
echo "RAG Backend Security & Vulnerability Checks"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo "Attempting to activate .venv..."
    if [ -d "../.venv" ]; then
        source ../.venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo -e "${RED}Error: No virtual environment found${NC}"
        exit 1
    fi
fi

# Function to run a check and handle errors
run_check() {
    local name=$1
    local command=$2
    local optional=$3
    
    echo "----------------------------------------"
    echo "Running: $name"
    echo "----------------------------------------"
    
    if eval "$command"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        echo ""
        return 0
    else
        if [ "$optional" = "true" ]; then
            echo -e "${YELLOW}⚠ $name failed (optional)${NC}"
            echo ""
            return 0
        else
            echo -e "${RED}✗ $name failed${NC}"
            echo ""
            return 1
        fi
    fi
}

# Track overall success
FAILED=0

# 1. Bandit - Python Security Linter
if ! run_check "Bandit Security Scan" "bandit -r app -c .bandit" "false"; then
    FAILED=1
fi

# 2. Safety - Dependency Vulnerability Check
if ! run_check "Safety Dependency Check" "safety check --json" "true"; then
    echo -e "${YELLOW}Note: Safety check failed. This may be due to outdated database or network issues.${NC}"
    echo ""
fi

# 3. Pip Audit - PyPI Package Vulnerability Scanner
if ! run_check "Pip-Audit Package Scanner" "pip-audit --desc" "true"; then
    echo -e "${YELLOW}Note: Pip-audit found vulnerabilities. Review and update packages if needed.${NC}"
    echo ""
fi

# 4. Check for hardcoded secrets (basic regex patterns)
echo "----------------------------------------"
echo "Checking for hardcoded secrets"
echo "----------------------------------------"
if grep -r -n -E "(password|secret|api_key|token)\\s*=\\s*['\"][^'\"]+['\"]" app/ --include="*.py" | grep -v "test" | grep -v "__pycache__"; then
    echo -e "${YELLOW}⚠ Potential hardcoded secrets found. Review the above matches.${NC}"
    echo ""
else
    echo -e "${GREEN}✓ No obvious hardcoded secrets detected${NC}"
    echo ""
fi

# 5. Check for dangerous imports
echo "----------------------------------------"
echo "Checking for potentially dangerous imports"
echo "----------------------------------------"
DANGEROUS_IMPORTS=$(grep -r -n -E "import (pickle|marshal|shelve|subprocess|eval|exec|compile)" app/ --include="*.py" | grep -v "__pycache__" || true)
if [ -n "$DANGEROUS_IMPORTS" ]; then
    echo -e "${YELLOW}⚠ Potentially dangerous imports found:${NC}"
    echo "$DANGEROUS_IMPORTS"
    echo ""
else
    echo -e "${GREEN}✓ No dangerous imports detected${NC}"
    echo ""
fi

# 6. Check for SQL injection patterns (if using raw SQL)
echo "----------------------------------------"
echo "Checking for potential SQL injection patterns"
echo "----------------------------------------"
SQL_PATTERNS=$(grep -r -n -E "execute\\([\"'][^\"']*%s" app/ --include="*.py" | grep -v "__pycache__" || true)
if [ -n "$SQL_PATTERNS" ]; then
    echo -e "${YELLOW}⚠ Potential SQL injection patterns found:${NC}"
    echo "$SQL_PATTERNS"
    echo ""
else
    echo -e "${GREEN}✓ No SQL injection patterns detected${NC}"
    echo ""
fi

# 7. Check Python version
echo "----------------------------------------"
echo "Python Version Check"
echo "----------------------------------------"
python --version
echo ""

# Summary
echo "=========================================="
echo "Security Check Summary"
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All critical security checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Some security checks failed. Please review the output above.${NC}"
    exit 1
fi
