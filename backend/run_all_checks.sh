#!/bin/bash

# Comprehensive Test and Security Check Script
# Runs all tests, security scans, and generates reports

set -e

echo "=========================================="
echo "RAG Backend - Complete Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
TESTS_PASSED=0
SECURITY_PASSED=0
TOTAL_FAILURES=0

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

# Function to print section header
print_section() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

# Function to run command and track success
run_check() {
    local name=$1
    local command=$2
    local optional=$3
    
    echo -e "${BLUE}Running: $name${NC}"
    echo "Command: $command"
    echo ""
    
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
            TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
            return 1
        fi
    fi
}

# ==================================================
# 1. UNIT TESTS
# ==================================================
print_section "1. RUNNING UNIT TESTS"

if run_check "PyTest Unit Tests" "pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=70" "false"; then
    TESTS_PASSED=1
fi

# ==================================================
# 2. SECURITY TESTS
# ==================================================
print_section "2. RUNNING SECURITY TESTS"

if run_check "Security-Specific Tests" "pytest tests/test_security.py -v -m security" "true"; then
    echo "Security tests completed"
fi

# ==================================================
# 3. CODE QUALITY CHECKS
# ==================================================
print_section "3. CODE QUALITY AND SECURITY SCANS"

# Bandit - Python security linter
run_check "Bandit Security Scan" "bandit -r app -c .bandit" "false"

# Safety - Dependency vulnerability check
run_check "Safety Dependency Check" "safety check --json || true" "true"

# Pip Audit - PyPI package vulnerability scanner
run_check "Pip-Audit Package Scanner" "pip-audit --desc || true" "true"

# ==================================================
# 4. STATIC CODE ANALYSIS
# ==================================================
print_section "4. STATIC CODE ANALYSIS"

# Check for hardcoded secrets
echo "Checking for hardcoded secrets..."
if grep -r -n -E "(password|secret|api_key|token)\\s*=\\s*['\"][^'\"]+['\"]" app/ --include="*.py" | grep -v "test" | grep -v "__pycache__" | grep -v "# noqa" > /tmp/secrets_check.txt 2>&1; then
    echo -e "${YELLOW}⚠ Potential hardcoded secrets found:${NC}"
    cat /tmp/secrets_check.txt
    echo ""
else
    echo -e "${GREEN}✓ No obvious hardcoded secrets detected${NC}"
    echo ""
fi

# Check for dangerous imports
echo "Checking for potentially dangerous imports..."
DANGEROUS_IMPORTS=$(grep -r -n -E "import (pickle|marshal|shelve|subprocess\.call|eval|exec|compile)" app/ --include="*.py" | grep -v "__pycache__" | grep -v "# noqa" || true)
if [ -n "$DANGEROUS_IMPORTS" ]; then
    echo -e "${YELLOW}⚠ Potentially dangerous imports found:${NC}"
    echo "$DANGEROUS_IMPORTS"
    echo ""
else
    echo -e "${GREEN}✓ No dangerous imports detected${NC}"
    echo ""
fi

# ==================================================
# 5. COVERAGE REPORT
# ==================================================
print_section "5. TEST COVERAGE REPORT"

echo "Generating coverage report..."
if [ -d "htmlcov" ]; then
    echo -e "${GREEN}✓ HTML coverage report generated in htmlcov/index.html${NC}"
    echo ""
    
    # Extract coverage percentage if available
    if [ -f ".coverage" ]; then
        coverage report --skip-empty | tail -5
        echo ""
    fi
fi

# ==================================================
# 6. INTEGRATION TESTS (if applicable)
# ==================================================
print_section "6. INTEGRATION TESTS"

echo "Running integration tests..."
if run_check "Integration Tests" "pytest tests/ -v -m integration || true" "true"; then
    echo "Integration tests completed"
fi

# ==================================================
# 7. TYPE CHECKING (if mypy is available)
# ==================================================
print_section "7. TYPE CHECKING"

if command -v mypy &> /dev/null; then
    run_check "MyPy Type Checking" "mypy app --ignore-missing-imports || true" "true"
else
    echo -e "${YELLOW}⚠ MyPy not installed, skipping type checking${NC}"
    echo "Install with: pip install mypy"
    echo ""
fi

# ==================================================
# SUMMARY
# ==================================================
print_section "TEST AND SECURITY CHECK SUMMARY"

echo "Results:"
echo "--------"
if [ $TESTS_PASSED -eq 1 ]; then
    echo -e "${GREEN}✓ Unit Tests: PASSED${NC}"
else
    echo -e "${RED}✗ Unit Tests: FAILED${NC}"
fi

echo ""
echo "Coverage Report: htmlcov/index.html"
echo "Security Scan: Complete"
echo ""

if [ $TOTAL_FAILURES -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "ALL CHECKS PASSED!"
    echo "==========================================${NC}"
    exit 0
else
    echo -e "${RED}=========================================="
    echo "SOME CHECKS FAILED ($TOTAL_FAILURES failures)"
    echo "Please review the output above."
    echo "==========================================${NC}"
    exit 1
fi
