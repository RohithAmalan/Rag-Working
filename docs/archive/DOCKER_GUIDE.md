# 🐳 Docker Setup Guide

## 📋 Prerequisites

- Docker Desktop installed and running
- At least 4GB RAM allocated to Docker
- 10GB free disk space

## 🚀 Quick Start

### 1. Create .env file

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```bash
GROQ_API_KEY=your_actual_groq_api_key
```

### 2. Start all services

```bash
# Production mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 3. Access the application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **MongoDB:** localhost:27017
- **Redis:** localhost:6379
- **MinIO Console:** http://localhost:9001 (if enabled)

### 4. Stop services

```bash
docker-compose down

# Stop and remove volumes (delete all data)
docker-compose down -v
```

---

## 🛠️ Development Mode

For hot-reload during development:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Changes to code will automatically reload the servers.

---

## 📦 Services Included

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | 5173 | React/Vite UI |
| **Backend** | 8000 | FastAPI server |
| **MongoDB** | 27017 | Vector database |
| **Redis** | 6379 | Response cache |
| **MinIO** | 9000, 9001 | S3 storage (optional) |

---

## 🔧 Useful Commands

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart a service
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Rebuild after code changes
```bash
# Rebuild all
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build backend
```

### Execute commands in container
```bash
# Open shell in backend
docker-compose exec backend bash

# Run pytest
docker-compose exec backend pytest

# Open MongoDB shell
docker-compose exec mongodb mongosh -u admin -p password123
```

### Check resource usage
```bash
docker stats
```

### Clean up
```bash
# Remove stopped containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove unused images
docker image prune -a

# Full cleanup
docker system prune -a --volumes
```

---

## 🌍 Environment Variables

Key variables in `.env`:

### Required
- `GROQ_API_KEY` - Your Groq API key

### MongoDB
- `MONGO_ROOT_USER` - MongoDB admin username
- `MONGO_ROOT_PASSWORD` - MongoDB admin password
- `MONGO_DB_NAME` - Database name

### Optional
- `MINIO_ENABLED` - Enable S3 storage (true/false)
- `REDIS_ENABLED` - Enable caching (true/false)
- `LANGGRAPH_WORKFLOW_MODE` - Workflow type (basic/advanced/multi_agent)

---

## 🐛 Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs backend

# Restart service
docker-compose restart backend
```

### Database connection issues
```bash
# Check MongoDB is healthy
docker-compose ps mongodb

# Check logs
docker-compose logs mongodb
```

### Port already in use
```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Changed from 8000:8000
```

### Out of disk space
```bash
# Clean up
docker system prune -a --volumes
```

### Rebuild from scratch
```bash
# Stop everything
docker-compose down -v

# Remove images
docker-compose rm -f

# Rebuild
docker-compose up -d --build
```

---

## 📊 Health Checks

All services have health checks:

```bash
# Check health status
docker-compose ps

# Services should show "healthy" in STATUS column
```

---

## 🚀 Production Deployment

### Build optimized images
```bash
docker-compose build --no-cache
```

### Push to registry
```bash
# Tag images
docker tag rag-backend:latest your-registry/rag-backend:latest
docker tag rag-frontend:latest your-registry/rag-frontend:latest

# Push
docker push your-registry/rag-backend:latest
docker push your-registry/rag-frontend:latest
```

### Deploy to cloud
- Railway: Connect GitHub repo, auto-deploy
- Render: Upload docker-compose.yml
- AWS ECS: Use Fargate with Docker Compose
- DigitalOcean: App Platform with Dockerfiles

---

## 💡 Tips

1. **First time:** Services take 2-3 minutes to start
2. **Logs:** Always check logs if something fails
3. **Volumes:** Data persists even after `docker-compose down`
4. **Rebuild:** Use `--build` flag after code changes
5. **Resources:** Monitor with `docker stats`

---

## 🎯 Next Steps

1. ✅ Start services: `docker-compose up -d`
2. ✅ Add your Groq API key to `.env`
3. ✅ Open http://localhost:5173
4. ✅ Upload files and test queries
5. ✅ Check logs: `docker-compose logs -f`

---

**Need help?** Check logs with `docker-compose logs -f` and look for error messages.
