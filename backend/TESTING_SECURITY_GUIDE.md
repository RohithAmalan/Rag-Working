# Testing and Security Guide

## Overview

This document describes the comprehensive testing and security infrastructure for the RAG backend application.

## 🧪 Testing Infrastructure

### Test Coverage

The backend includes extensive unit tests covering:

- **Services**:
  - `embedding_service` - Embedding generation and similarity calculations
  - `file_service` - File upload, validation, and processing
  - `minio_service` - Object storage operations
  - `mongo_vector_service` - Vector search and document storage
  - `rag_service` - Complete RAG pipeline orchestration
  - `auth_service` - Authentication and authorization
  - `keycloak_service` - Keycloak integration

- **Routes**:
  - `auth_routes` - Authentication endpoints
  - `rag_routes` - RAG operations with RBAC
  - `system_routes` - System health and status
  - `evaluation_routes` - RAG evaluation metrics

- **RAG Components**:
  - `chunking` - Text and data chunking strategies
  - `citation_generator` - Source citation generation
  - `query_expansion` - Query enhancement
  - `reranker` - Result reranking
  - `semantic_chunker` - Semantic chunking
  - `rag_generator` - Answer generation

- **Security**:
  - Input validation and sanitization
  - Path traversal prevention
  - File type restrictions
  - Authentication and authorization
  - Injection attack prevention

### Test Organization

```
backend/tests/
├── conftest.py                    # Shared test fixtures
├── test_auth_routes.py           # Authentication endpoint tests
├── test_auth_service.py          # Auth service tests
├── test_chunking.py              # Chunking logic tests
├── test_citation_generator.py    # Citation generation tests
├── test_embedding_service.py     # NEW: Embedding service tests
├── test_evaluation_routes.py     # NEW: Evaluation endpoint tests
├── test_file_service.py          # NEW: File handling tests
├── test_minio_service.py         # NEW: MinIO storage tests
├── test_mongo_vector_service.py  # NEW: Vector search tests
├── test_rag_service.py           # NEW: RAG orchestration tests
├── test_security.py              # NEW: Security-focused tests
└── ...
```

## 🛡️ Security Scanning

### Tools Included

1. **Bandit** - Python security linter
   - Scans for common security issues
   - Checks for hardcoded credentials
   - Identifies dangerous function calls
   - Configuration: `.bandit`

2. **Safety** - Dependency vulnerability scanner
   - Checks dependencies against CVE database
   - Identifies known vulnerabilities
   - Configuration: `.safety-policy.yml`

3. **Pip-Audit** - PyPI package auditor
   - Audits packages for known vulnerabilities
   - Provides detailed vulnerability descriptions

### Security Test Coverage

- **Input Validation**:
  - SQL/NoSQL injection prevention
  - XSS attack prevention
  - Path traversal protection
  
- **File Upload Security**:
  - File type restrictions
  - Size limit handling
  - Malicious content detection
  
- **Authentication**:
  - Token validation
  - Authorization checks
  - Invalid credential handling
  
- **Data Security**:
  - Sensitive data handling
  - Error message sanitization
  - Log content validation

## 🚀 Running Tests

### Quick Start

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source ../.venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

### Run Specific Test Categories

```bash
# Run only security tests
pytest tests/test_security.py -v

# Run service tests
pytest tests/test_*_service.py -v

# Run route tests
pytest tests/test_*_routes.py -v

# Run with specific markers
pytest -m security -v
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/ --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🔒 Running Security Checks

### Comprehensive Security Scan

```bash
# Run all security checks
./run_security_checks.sh
```

This script performs:
1. Bandit security scan
2. Safety dependency check
3. Pip-audit package scan
4. Hardcoded secret detection
5. Dangerous import detection
6. SQL injection pattern check

### Individual Security Tools

```bash
# Run Bandit
bandit -r app -c .bandit

# Run Safety
safety check --json

# Run Pip-Audit
pip-audit --desc
```

## 📊 Complete Test Suite

### Run Everything

```bash
# Run all tests and security checks
./run_all_checks.sh
```

This comprehensive script performs:
1. ✅ Unit tests with coverage
2. ✅ Security-specific tests
3. ✅ Code quality scans
4. ✅ Static code analysis
5. ✅ Coverage reporting
6. ✅ Integration tests (if available)
7. ✅ Type checking (if mypy installed)

### Output

The script provides:
- Color-coded results
- Detailed error messages
- Coverage statistics
- Security scan reports
- Final summary

## 🔧 Configuration Files

### pytest.ini

```ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    -v
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=70
```

### .bandit

```ini
[bandit]
exclude_dirs = /tests/,/.venv/,/venv/,/__pycache__/,/htmlcov/
skips = B101
severity = MEDIUM
confidence = MEDIUM
```

## 📈 Coverage Goals

- **Target Coverage**: 70% minimum
- **Current Coverage**: Run `./run_all_checks.sh` to see current metrics
- **Focus Areas**: Business logic, security-critical code

## 🎯 Best Practices

### Writing Tests

1. **Use descriptive test names**:
   ```python
   def test_upload_file_validates_type():
       """Test that file upload validates file types."""
   ```

2. **Follow AAA pattern** (Arrange, Act, Assert):
   ```python
   def test_example():
       # Arrange
       service = MyService()
       
       # Act
       result = service.do_something()
       
       # Assert
       assert result == expected
   ```

3. **Mock external dependencies**:
   ```python
   @patch("app.services.my_service.external_api")
   def test_with_mock(mock_api):
       mock_api.return_value = {"data": "test"}
       # ... test code
   ```

4. **Test error cases**:
   ```python
   def test_handles_invalid_input():
       with pytest.raises(ValueError):
           service.process(invalid_input)
   ```

### Security Testing

1. **Test authentication**:
   - Verify protected endpoints require auth
   - Test invalid token rejection
   - Check authorization levels

2. **Test input validation**:
   - SQL/NoSQL injection attempts
   - Path traversal attempts
   - XSS attacks
   - Large file uploads

3. **Test data security**:
   - No sensitive data in logs
   - Error messages don't leak info
   - Proper data sanitization

## 🔄 Continuous Integration

### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/tests.yml`) that:

- Runs on every push and PR
- Tests multiple Python versions (3.10, 3.11, 3.12)
- Executes all tests with coverage
- Runs security scans
- Uploads coverage reports
- Checks for hardcoded secrets

### Local Pre-commit Checks

Before committing:

```bash
# Run quick checks
pytest tests/ -v --cov=app --cov-fail-under=70

# Run security scan
./run_security_checks.sh

# Or run everything
./run_all_checks.sh
```

## 📝 Test Maintenance

### Adding New Tests

1. Create test file: `tests/test_new_feature.py`
2. Import necessary modules
3. Write test class and methods
4. Run tests to verify
5. Check coverage

### Updating Tests

When modifying code:
1. Update related tests
2. Add new tests for new functionality
3. Ensure coverage doesn't decrease
4. Run full test suite before committing

## 🐛 Debugging Failed Tests

### Common Issues

1. **Import errors**: Check virtual environment is activated
2. **Missing fixtures**: Check `conftest.py`
3. **Async issues**: Ensure `pytest-asyncio` is installed
4. **Mock errors**: Verify mock paths are correct

### Debug Mode

```bash
# Run with verbose output
pytest tests/ -vv

# Stop on first failure
pytest tests/ -x

# Show local variables on failure
pytest tests/ -l

# Run specific test
pytest tests/test_file.py::TestClass::test_method -v
```

## 📚 Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Bandit documentation](https://bandit.readthedocs.io/)
- [Safety documentation](https://pyup.io/safety/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

## 🎓 Testing Checklist

Before releasing:

- [ ] All unit tests pass
- [ ] Coverage is at least 70%
- [ ] Security scans pass
- [ ] No hardcoded secrets
- [ ] No dangerous imports
- [ ] Integration tests pass
- [ ] Performance tests pass (if applicable)
- [ ] Documentation is updated

## 🆘 Getting Help

If you encounter issues:

1. Check test output for specific errors
2. Review this documentation
3. Check GitHub Actions logs (if using CI/CD)
4. Review pytest and security tool documentation
5. Check existing test examples in `tests/` directory

---

**Last Updated**: 2024
**Maintainer**: RAG Backend Team
