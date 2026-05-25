# Docker Configuration Guide

## Overview

The RAG application now uses a **unified Docker Compose configuration** with profile-based environment switching.

## Usage

### Production Mode (Default)
```bash
docker-compose up
```

This runs:
- MongoDB
- Redis
- MinIO
- Backend (production build, no hot-reload)
- Frontend (Nginx production serving)

### Development Mode
```bash
docker-compose --profile dev up
```

This runs:
- MongoDB
- Redis  
- MinIO
- Backend-dev (hot-reload enabled, volume-mounted source)
- Frontend-dev (Vite dev server, hot-reload enabled)

## What Changed

### Before
- `docker-compose.yml` - Production configuration
- `docker-compose.dev.yml` - Development overrides
- Had to use: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`

### After
- **Single `docker-compose.yml`** with profiles
- `backend` and `frontend` services have `profiles: [prod, default]`
- `backend-dev` and `frontend-dev` services have `profiles: [dev]`
- Simpler commands, easier to maintain

## Benefits

1. **Single source of truth** - All Docker config in one file
2. **Clearer separation** - Explicit dev vs prod services
3. **Easier to use** - No need to specify multiple `-f` flags
4. **Self-documenting** - Profile names clearly indicate purpose

## Environment Variables

All environment variables are read from `.env` file (same as before):

```env
# MongoDB
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=password123
MONGO_DB_NAME=rag_db

# MinIO (optional)
MINIO_ENABLED=false

# Groq API
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-70b-versatile

# LangGraph
LANGGRAPH_WORKFLOW_MODE=multi_agent
```

## Migration Notes

- The old `docker-compose.dev.yml` is no longer needed
- Existing production deployments continue to work without changes (`docker-compose up`)
- To enable development mode, simply add `--profile dev`

## Common Commands

```bash
# Production
docker-compose up -d                    # Start in background
docker-compose down                     # Stop services
docker-compose logs -f backend          # View backend logs

# Development
docker-compose --profile dev up         # Start dev mode
docker-compose --profile dev down       # Stop dev services
docker-compose --profile dev logs -f backend-dev  # View dev backend logs

# Rebuild
docker-compose build                    # Rebuild production images
docker-compose --profile dev build      # Rebuild dev images
```

## Notes

- Development mode mounts source code as volumes for hot-reload
- Production mode uses optimized builds with no volume mounts
- Both modes share the same MongoDB, Redis, and MinIO instances
- Health checks are configured for all services
