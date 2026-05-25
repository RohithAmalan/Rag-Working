# Testing & Code Quality Setup

## 📋 Overview

Comprehensive unit testing and code quality analysis setup for the RAG application backend.

## 🧪 Test Suite

### Test Files Created

1. **test_dependencies.py** - RBAC authentication & authorization tests
   - Token validation (Keycloak + legacy)
   - Admin role enforcement
   - User authentication
   - Optional authentication

2. **test_constants.py** - Constants validation
   - Roles definition tests
   - API messages validation
   - Helper methods testing

3. **test_keycloak_service.py** - Keycloak integration tests
   - JWT token verification
   - Role extraction from realm_access
   - Flexible issuer validation (localhost + host.docker.internal)
   - ROPC credential exchange
   - Token revocation

4. **test_rag_routes_rbac.py** - RAG routes with RBAC
   - Upload endpoint (all authenticated users)
   - Delete endpoint (admin only)
   - Query endpoint (all authenticated users)
   - List endpoint (all authenticated users)
   - Unauthorized access blocked

### Existing Tests

- test_auth_routes.py - Authentication API tests
- test_auth_service.py - Auth service tests
- test_chunking.py - Document chunking tests
- test_citation_generator.py - Citation generation tests
- test_query_expansion.py - Query expansion tests
- test_rag_generator.py - RAG generation tests
- test_reranker.py - Reranking tests
- test_semantic_chunker.py - Semantic chunking tests
- test_system_routes.py - System routes tests

## 🚀 Running Tests

### Quick Run
```bash
cd backend
python3 -m pytest tests/ -v
```

### With Coverage
```bash
python3 -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

### Run Specific Test File
```bash
python3 -m pytest tests/test_constants.py -v
python3 -m pytest tests/test_dependencies.py -v
python3 -m pytest tests/test_keycloak_service.py -v
python3 -m pytest tests/test_rag_routes_rbac.py -v
```

### Run All Tests + Quality Checks
```bash
./run_tests.sh
```

This script runs:
- ✅ All unit tests with coverage
- ✅ Security checks (Bandit)
- ✅ Code quality checks (Flake8)

## 📊 CodeQL Setup

### GitHub Actions Workflow

Created `.github/workflows/codeql-analysis.yml` with:

#### 1. CodeQL Security Analysis
- **Languages**: Python, JavaScript/TypeScript
- **Queries**: security-and-quality, security-extended
- **Schedule**: Weekly (Sundays at 00:00 UTC)
- **Triggers**: Push to main/develop/feature branches, PRs

#### 2. Dependency Security Scan
- Python: Safety check for known vulnerabilities
- Node.js: npm audit for frontend dependencies

#### 3. Code Quality Checks
- **Python**:
  - Flake8 (linting)
  - Bandit (security linting)
  - Black (code formatting)
  - isort (import ordering)
- **JavaScript**:
  - ESLint

#### 4. Test Coverage Analysis
- Automated coverage reports
- PR comments with coverage details
- HTML reports as artifacts

### Running CodeQL Locally

CodeQL requires the GitHub CodeQL CLI. For local analysis:

```bash
# Install CodeQL CLI
https://github.com/github/codeql-cli-binaries/releases

# Run analysis
codeql database create backend-db --language=python --source-root=backend
codeql database analyze backend-db python-security-and-quality.qls --format=sarif-latest --output=results.sarif
```

## 🔍 Coverage Requirements

- **Minimum Coverage**: 70% (configured in pytest.ini)
- **Coverage Report**: `backend/htmlcov/index.html`
- **Coverage Formats**:
  - Terminal (term-missing)
  - HTML (htmlcov/)
  - XML (coverage.xml for CI)

## 📝 Test Coverage Goals

### Current Test Coverage Areas

✅ **Authentication & Authorization**
- Token validation (Keycloak + legacy)
- Role-based access control
- Admin vs user permissions

✅ **Constants & Configuration**
- Role definitions
- API message strings
- Validation helpers

✅ **Keycloak Integration**
- JWT verification
- Role extraction
- Issuer validation
- Token exchange & revocation

✅ **RAG Endpoints**
- Upload (authenticated users)
- Query (authenticated users)
- Delete (admin only)
- List (authenticated users)

✅ **RAG Components**
- Document chunking
- Query expansion
- Semantic chunking
- Reranking
- Citation generation

## 🛠️ Dependencies for Testing

### Required Packages

```bash
pip install pytest pytest-cov pytest-asyncio
pip install flake8 bandit black isort safety
```

### Test Configuration

Located in `pytest.ini`:
- Test discovery pattern: `test_*.py`
- Async mode: auto
- Coverage minimum: 70%
- Warnings filtered

## 🎯 Quality Metrics

### Code Quality Tools

1. **Flake8** - Python linting
   - Error checking (E9, F63, F7, F82)
   - Complexity analysis (max: 10)
   - Line length (max: 127)

2. **Bandit** - Security linting
   - Common security issues
   - Hardcoded secrets detection
   - Unsafe function usage

3. **Black** - Code formatting
   - PEP 8 compliance
   - Consistent style

4. **isort** - Import organization
   - Sorted imports
   - Proper grouping

5. **Safety** - Dependency vulnerability checking
   - Known CVEs in dependencies
   - Security advisories

## 📈 CI/CD Integration

### GitHub Actions Workflows

1. **codeql-analysis.yml** - Security & quality analysis
2. **backend-ci.yml** - Backend CI (existing)
3. **frontend-ci.yml** - Frontend CI (existing)
4. **integration-test.yml** - Integration tests (existing)

### Workflow Triggers

- **Push**: main, develop, feature-* branches
- **Pull Request**: main, develop branches
- **Schedule**: Weekly security scans

## 🔐 Security Best Practices

### Tested Security Features

- ✅ JWT token validation
- ✅ Role-based access control
- ✅ Authorization header verification
- ✅ Admin permission enforcement
- ✅ Token expiration handling
- ✅ Secure token revocation
- ✅ Flexible issuer validation (containerized env)

### Security Scans

- CodeQL weekly scans
- Dependency vulnerability checks
- Bandit security linting
- npm audit (frontend)

## 📚 Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [CodeQL documentation](https://codeql.github.com/docs/)
- [Bandit documentation](https://bandit.readthedocs.io/)
- [Flake8 documentation](https://flake8.pycqa.org/)

## 🎉 Next Steps

1. ✅ Run test suite: `./run_tests.sh`
2. ✅ Check coverage report: `open htmlcov/index.html`
3. ✅ Push to GitHub to trigger CodeQL
4. ✅ Review security findings in GitHub Security tab
5. ✅ Monitor test coverage on PRs
6. ✅ Address any quality issues flagged by linters
