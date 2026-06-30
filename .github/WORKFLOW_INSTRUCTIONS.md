# GitHub Workflow & CI/CD Instructions

Complete guide for GitHub Actions workflows, CI/CD pipelines, and automation for the RAG application.

==================================================
🎯 PURPOSE
==================================================

Automate testing, security scanning, building, and deployment processes using GitHub Actions.

Goals:
- Automated testing on every push/PR
- Security vulnerability scanning
- Code quality checks
- Docker image building
- Automated deployment
- Coverage reporting

==================================================
🧠 WORKFLOW STRUCTURE
==================================================

Recommended structure:

```
.github/
├── workflows/
│   ├── tests.yml              # Backend tests + security
│   ├── frontend-tests.yml     # Frontend tests
│   ├── build-backend.yml      # Build backend Docker image
│   ├── build-frontend.yml     # Build frontend Docker image
│   ├── deploy-staging.yml     # Deploy to staging
│   ├── deploy-production.yml  # Deploy to production
│   └── codeql.yml            # Code security analysis
├── WORKFLOW_INSTRUCTIONS.md   # This file
└── dependabot.yml            # Dependency updates
```

==================================================
⚙️ EXISTING WORKFLOWS
==================================================

### 1. Backend Tests Workflow (tests.yml)

**Location**: `.github/workflows/tests.yml`

**Triggers**:
- Push to `main`, `develop`, `feature-*` branches
- Pull requests to `main`, `develop`

**Jobs**:
1. **Test** - Run pytest with multiple Python versions
   - Python 3.10, 3.11, 3.12
   - Install dependencies
   - Run unit tests
   - Generate coverage report

2. **Security Scan** - Vulnerability scanning
   - Bandit (Python security linter)
   - Safety (dependency checker)
   - pip-audit (PyPI vulnerabilities)
   - Check for hardcoded secrets

3. **Upload Coverage** - Send to Codecov
   - Coverage reports
   - Badge generation

**Configuration**:
```yaml
name: Backend Tests and Security

on:
  push:
    branches: [main, develop, 'feature-*']
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run tests with coverage
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml
```

==================================================
📝 WORKFLOW BEST PRACTICES
==================================================

### General Rules

1. **Use specific action versions** (not @latest)
   ```yaml
   - uses: actions/checkout@v4  # ✅ Good
   - uses: actions/checkout@latest  # ❌ Bad
   ```

2. **Cache dependencies** for faster runs
   ```yaml
   - name: Cache pip packages
     uses: actions/cache@v4
     with:
       path: ~/.cache/pip
       key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
   ```

3. **Use matrix builds** for multiple versions
   ```yaml
   strategy:
     matrix:
       python-version: ['3.10', '3.11', '3.12']
       node-version: [18, 20]
   ```

4. **Set timeouts** to prevent stuck jobs
   ```yaml
   jobs:
     test:
       timeout-minutes: 30
   ```

5. **Use secrets** for sensitive data
   ```yaml
   env:
     API_KEY: ${{ secrets.API_KEY }}
   ```

==================================================
🐳 DOCKER BUILD WORKFLOWS
==================================================

### Backend Docker Build

**File**: `.github/workflows/build-backend.yml`

```yaml
name: Build Backend Docker Image

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
      - '.github/workflows/build-backend.yml'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/backend

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Frontend Docker Build

**File**: `.github/workflows/build-frontend.yml`

```yaml
name: Build Frontend Docker Image

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
      - '.github/workflows/build-frontend.yml'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/frontend

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Build frontend
        run: |
          cd frontend
          npm ci
          npm run build

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
```

==================================================
🔒 SECURITY WORKFLOWS
==================================================

### CodeQL Security Analysis

**File**: `.github/workflows/codeql.yml`

```yaml
name: CodeQL Security Analysis

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Mondays

jobs:
  analyze:
    name: Analyze Code
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      actions: read
      contents: read

    strategy:
      matrix:
        language: ['python', 'javascript']

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}

      - name: Autobuild
        uses: github/codeql-action/autobuild@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
```

### Dependency Scanning

**File**: `.github/workflows/dependency-scan.yml`

```yaml
name: Dependency Vulnerability Scan

on:
  schedule:
    - cron: '0 0 * * *'  # Daily
  push:
    branches: [main]

jobs:
  scan-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install pip-audit safety
      
      - name: Run pip-audit
        run: |
          cd backend
          pip-audit --desc
        continue-on-error: true
      
      - name: Run Safety check
        run: |
          cd backend
          safety check --json
        continue-on-error: true

  scan-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run npm audit
        run: |
          cd frontend
          npm audit --audit-level=moderate
        continue-on-error: true
```

==================================================
🚀 DEPLOYMENT WORKFLOWS
==================================================

### Deploy to Staging

**File**: `.github/workflows/deploy-staging.yml`

```yaml
name: Deploy to Staging

on:
  push:
    branches: [develop]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Deploy to staging server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/rag-app
            git pull origin develop
            docker-compose down
            docker-compose up -d --build
            docker-compose ps
```

### Deploy to Production

**File**: `.github/workflows/deploy-production.yml`

```yaml
name: Deploy to Production

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Deploy to production
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/rag-app
            git pull origin main
            docker-compose -f docker-compose.prod.yml down
            docker-compose -f docker-compose.prod.yml up -d --build
            docker-compose -f docker-compose.prod.yml ps
      
      - name: Run health check
        run: |
          sleep 30
          curl -f https://api.example.com/health || exit 1
      
      - name: Notify deployment
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

==================================================
📊 COVERAGE & QUALITY WORKFLOWS
==================================================

### Code Coverage

**File**: `.github/workflows/coverage.yml`

```yaml
name: Code Coverage Report

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  coverage:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest-cov
      
      - name: Generate coverage report
        run: |
          cd backend
          pytest tests/ --cov=app --cov-report=xml --cov-report=html
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          file: ./backend/coverage.xml
          fail_ci_if_error: true
      
      - name: Archive coverage report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: backend/htmlcov/
```

==================================================
🔧 DEPENDABOT CONFIGURATION
==================================================

**File**: `.github/dependabot.yml`

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    reviewers:
      - "your-team"
    assignees:
      - "your-username"
    labels:
      - "dependencies"
      - "python"

  # Node.js dependencies
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    reviewers:
      - "your-team"
    labels:
      - "dependencies"
      - "javascript"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
    labels:
      - "dependencies"
      - "github-actions"

  # Docker
  - package-ecosystem: "docker"
    directory: "/backend"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"
```

==================================================
🎯 SECRETS MANAGEMENT
==================================================

### Required Secrets

Configure these in **Settings → Secrets and variables → Actions**:

**Backend**:
```
CODECOV_TOKEN              # Codecov upload token
GROQ_API_KEY              # Groq LLM API key
MONGODB_URI               # MongoDB connection string
KEYCLOAK_CLIENT_SECRET    # Keycloak client secret
MINIO_ACCESS_KEY          # MinIO access key
MINIO_SECRET_KEY          # MinIO secret key
```

**Frontend**:
```
VITE_API_URL              # Backend API URL
VITE_KEYCLOAK_URL         # Keycloak server URL
VITE_KEYCLOAK_REALM       # Keycloak realm name
VITE_KEYCLOAK_CLIENT_ID   # Keycloak client ID
```

**Deployment**:
```
STAGING_HOST              # Staging server hostname
STAGING_USER              # SSH username for staging
PROD_HOST                 # Production server hostname
PROD_USER                 # SSH username for production
SSH_PRIVATE_KEY           # SSH private key for deployment
SLACK_WEBHOOK             # Slack webhook for notifications
```

### Using Secrets in Workflows

```yaml
steps:
  - name: Run tests with secrets
    env:
      API_KEY: ${{ secrets.GROQ_API_KEY }}
      DB_URI: ${{ secrets.MONGODB_URI }}
    run: |
      pytest tests/
```

==================================================
🧪 TESTING WORKFLOWS
==================================================

### Frontend Tests

**File**: `.github/workflows/frontend-tests.yml`

```yaml
name: Frontend Tests

on:
  push:
    branches: [main, develop, 'feature-*']
    paths:
      - 'frontend/**'
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [18, 20]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run linter
        run: |
          cd frontend
          npm run lint
      
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage
      
      - name: Build
        run: |
          cd frontend
          npm run build
```

==================================================
📋 WORKFLOW TRIGGERS
==================================================

### Common Trigger Patterns

**On Push**:
```yaml
on:
  push:
    branches:
      - main
      - develop
      - 'feature/**'
    paths:
      - 'backend/**'
      - '.github/workflows/**'
```

**On Pull Request**:
```yaml
on:
  pull_request:
    branches:
      - main
      - develop
    types:
      - opened
      - synchronize
      - reopened
```

**On Schedule** (Cron):
```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
    - cron: '0 0 * * 1'  # Weekly on Monday
```

**Manual Trigger**:
```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production
```

**On Release**:
```yaml
on:
  release:
    types: [published, created]
```

==================================================
🔍 DEBUGGING WORKFLOWS
==================================================

### Enable Debug Logging

Add repository secrets:
```
ACTIONS_RUNNER_DEBUG = true
ACTIONS_STEP_DEBUG = true
```

### Useful Debug Steps

```yaml
- name: Debug environment
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Branch: ${{ github.ref }}"
    echo "SHA: ${{ github.sha }}"
    echo "Runner OS: ${{ runner.os }}"
    env

- name: Debug context
  run: |
    echo '${{ toJSON(github) }}'
    echo '${{ toJSON(secrets) }}'  # Don't do this in production!
```

==================================================
⚡ PERFORMANCE OPTIMIZATION
==================================================

### Caching Strategies

**Python Dependencies**:
```yaml
- name: Cache pip packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('backend/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

**Node Dependencies**:
```yaml
- name: Cache node modules
  uses: actions/cache@v4
  with:
    path: frontend/node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('frontend/package-lock.json') }}
```

**Docker Layers**:
```yaml
- name: Build with cache
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Parallel Jobs

```yaml
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    # ... backend test steps
  
  frontend-tests:
    runs-on: ubuntu-latest
    # ... frontend test steps
  
  security-scan:
    runs-on: ubuntu-latest
    # ... security scan steps
```

==================================================
✅ WORKFLOW STATUS BADGES
==================================================

### Add to README.md

```markdown
# RAG Application

![Backend Tests](https://github.com/username/repo/workflows/Backend%20Tests/badge.svg)
![Frontend Tests](https://github.com/username/repo/workflows/Frontend%20Tests/badge.svg)
![CodeQL](https://github.com/username/repo/workflows/CodeQL/badge.svg)
[![codecov](https://codecov.io/gh/username/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/username/repo)
```

==================================================
🎯 BEST PRACTICES SUMMARY
==================================================

✅ **DO**:
- Use specific action versions (@v4, not @latest)
- Cache dependencies
- Set job timeouts
- Use matrix builds for multiple versions
- Separate concerns (testing, building, deploying)
- Use environments for staging/production
- Enable branch protection rules
- Review workflow logs regularly
- Use secrets for sensitive data
- Add status badges to README

❌ **DON'T**:
- Hardcode credentials in workflows
- Use @latest for action versions
- Run long-running jobs without timeouts
- Deploy to production without tests passing
- Ignore failed workflows
- Commit secrets to repository
- Skip security scans

==================================================
🎓 RESOURCES
==================================================

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Workflow Syntax**: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- **Action Marketplace**: https://github.com/marketplace?type=actions
- **Security Hardening**: https://docs.github.com/en/actions/security-guides

==================================================
🎯 GOAL
==================================================

Maintain robust, efficient, and secure CI/CD pipelines that:

✅ Automate testing and quality checks
✅ Scan for security vulnerabilities
✅ Build and deploy applications reliably
✅ Provide fast feedback to developers
✅ Maintain high code quality standards
✅ Enable safe and confident deployments
