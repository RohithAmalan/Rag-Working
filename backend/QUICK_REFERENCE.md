# Quick Reference: Testing & Security

## 🚀 Run Commands

### Run All Tests & Security Checks
```bash
cd backend
./run_all_checks.sh
```

### Run Unit Tests Only
```bash
pytest tests/ -v --cov=app --cov-report=html
```

### Run Security Scans Only
```bash
./run_security_checks.sh
```

### Run Specific Test File
```bash
pytest tests/test_security.py -v
pytest tests/test_embedding_service.py -v
pytest tests/test_file_service.py -v
```

### Run Tests by Marker
```bash
pytest -m security -v
pytest -m integration -v
```

### View Coverage Report
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🔍 Individual Security Tools

### Bandit (Code Security)
```bash
bandit -r app -c .bandit
```

### Safety (Dependency Vulnerabilities)
```bash
safety check --json
```

### Pip-Audit (Package Vulnerabilities)
```bash
pip-audit --desc
```

## 📊 Coverage Commands

### Generate Coverage Report
```bash
pytest --cov=app --cov-report=term-missing
```

### Check Coverage Threshold
```bash
pytest --cov=app --cov-fail-under=70
```

### Generate XML Coverage (for CI/CD)
```bash
pytest --cov=app --cov-report=xml
```

## 🐛 Debugging Tests

### Verbose Output
```bash
pytest tests/ -vv
```

### Stop on First Failure
```bash
pytest tests/ -x
```

### Show Local Variables on Failure
```bash
pytest tests/ -l
```

### Run Last Failed Tests
```bash
pytest --lf
```

### Run with PDB on Failure
```bash
pytest --pdb
```

## 📝 Test Structure

### Test File Naming
- `test_*.py` - Test files
- `*_test.py` - Alternative pattern

### Test Function Naming
- `test_<feature>_<scenario>()`
- Example: `test_upload_file_validates_type()`

### Test Class Naming
- `class Test<Feature>:`
- Example: `class TestAuthenticationSecurity:`

## 🛠️ Useful Pytest Options

```bash
# Run with custom markers
pytest -m "not slow" -v

# Run specific test
pytest tests/test_file.py::TestClass::test_method

# Parallel execution (requires pytest-xdist)
pytest -n auto

# Generate JUnit XML (for CI)
pytest --junitxml=report.xml

# Run with coverage and generate multiple reports
pytest --cov=app --cov-report=term --cov-report=html --cov-report=xml
```

## 🎯 Test Fixtures

Located in `tests/conftest.py`:
- `client` - FastAPI test client
- `mock_db` - Mocked database
- `valid_credentials` - Test credentials
- `file_service` - File service instance

## 🔒 Security Checklist

Before committing:
- [ ] All tests pass
- [ ] Coverage ≥ 70%
- [ ] Bandit scan clean
- [ ] No hardcoded secrets
- [ ] No dangerous imports
- [ ] Safety check passed

## 📚 Documentation

- **Full Guide**: `TESTING_SECURITY_GUIDE.md`
- **Summary**: `SUMMARY.md`
- **Configuration**: `pytest.ini`, `.bandit`, `.safety-policy.yml`

## 🌐 CI/CD

GitHub Actions workflow: `.github/workflows/tests.yml`
- Runs on push/PR
- Tests Python 3.10, 3.11, 3.12
- Uploads coverage to Codecov

## 🆘 Common Issues

### Import Errors
```bash
# Ensure venv is activated
source ../.venv/bin/activate
```

### Mock Path Errors
```python
# Use full module path in patch
@patch("app.services.my_service.external_function")
```

### Async Test Issues
```python
# Use pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function():
    ...
```

## 📊 Test Statistics

- **Total Tests**: 100+
- **Test Files**: 14
- **Coverage Target**: 70%
- **Security Tools**: 3

## 🔗 Quick Links

- [pytest docs](https://docs.pytest.org/)
- [Bandit docs](https://bandit.readthedocs.io/)
- [Safety docs](https://pyup.io/safety/)
- [Coverage.py docs](https://coverage.readthedocs.io/)

---
**Last Updated**: May 2026
