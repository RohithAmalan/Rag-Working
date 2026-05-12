# Production Deployment Guide

## Pre-Deployment Checklist

### Security
- [ ] API keys stored in environment variables
- [ ] CORS configured for production domain only
- [ ] Database credentials never in git
- [ ] SSL/TLS certificates obtained
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] Logging doesn't expose sensitive data

### Testing
- [ ] All unit tests passing
- [ ] Integration tests with MongoDB Atlas
- [ ] Load testing (100+ concurrent requests)
- [ ] Embedding generation performance tested
- [ ] Vector search queries optimized
- [ ] LLM API responses validated

### Infrastructure
- [ ] MongoDB Atlas cluster created (M10+ for production)
- [ ] Database backups enabled
- [ ] Network security groups configured
- [ ] IP whitelist set in MongoDB Atlas
- [ ] Connection strings validated

### Documentation
- [ ] README updated with deployment info
- [ ] API documentation complete
- [ ] Monitoring setup documented
- [ ] Rollback procedure documented

---

## Deployment Strategies

### Strategy 1: Docker Containerization

#### 1. Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY .env .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Create docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  rag-backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      MONGODB_URI: ${MONGODB_URI}
      GROQ_API_KEY: ${GROQ_API_KEY}
      EMBEDDING_MODEL: all-MiniLM-L6-v2
    volumes:
      - ./app/uploads:/app/app/uploads
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 3. Build and Run

```bash
# Build image
docker build -t rag-backend:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e MONGODB_URI="mongodb+srv://..." \
  -e GROQ_API_KEY="..." \
  --name rag-backend \
  rag-backend:latest

# Or use docker-compose
docker-compose up -d
```

### Strategy 2: Cloud Platform Deployment

#### Deployment on AWS (EC2 + RDS)

```bash
# 1. Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name my-key \
  --security-groups rag-backend

# 2. Connect and setup
ssh -i my-key.pem ec2-user@<instance-ip>

# 3. Install dependencies
sudo yum update
sudo yum install python3 python3-pip git

# 4. Clone repository
git clone https://github.com/your-repo/rag-backend.git
cd rag-backend

# 5. Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Configure environment
cp .github/config/.env.example .env
# Edit .env with production values

# 7. Start backend with systemd
sudo cp deployment/rag-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start rag-backend
sudo systemctl enable rag-backend
```

#### Deployment on Google Cloud Run

```bash
# 1. Build image
gcloud builds submit --tag gcr.io/PROJECT_ID/rag-backend

# 2. Deploy to Cloud Run
gcloud run deploy rag-backend \
  --image gcr.io/PROJECT_ID/rag-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars MONGODB_URI="...",GROQ_API_KEY="..." \
  --allow-unauthenticated

# 3. Get service URL
gcloud run services list
```

#### Deployment on Heroku

```bash
# 1. Install Heroku CLI and login
heroku login

# 2. Create app
heroku create rag-backend

# 3. Set environment variables
heroku config:set MONGODB_URI="mongodb+srv://..."
heroku config:set GROQ_API_KEY="..."

# 4. Deploy
git push heroku main

# 5. View logs
heroku logs --tail
```

---

## Environment Setup

### 1. MongoDB Atlas Setup

```bash
# 1. Create MongoDB Atlas account
# https://cloud.mongodb.com

# 2. Create cluster (M10 or higher for production)
# - Choose AWS/GCP/Azure as provider
# - Select closest region

# 3. Create database user
# Username: rag_app
# Password: <strong_password>

# 4. Setup IP whitelist
# Add your server IP (or 0.0.0.0/0 for development)

# 5. Get connection string
# mongodb+srv://rag_app:password@cluster0.abc123.mongodb.net/?retryWrites=true&w=majority

# 6. Create vector search index (in MongoDB Atlas console)
# Collection: chunks
# Field: embedding
# Similarity: cosine
```

### 2. Environment Variables

Create `.env` file with production values:

```bash
# MongoDB
MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"
DATABASE_NAME="rag_db"

# Groq API
GROQ_API_KEY="gsk_..."

# Embeddings
EMBEDDING_MODEL="all-MiniLM-L6-v2"
EMBEDDING_DIMENSION=384
BATCH_SIZE=32

# FastAPI
ENV="production"
DEBUG=False
LOG_LEVEL="INFO"

# CORS
ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"

# File Upload
MAX_FILE_SIZE_MB=100
UPLOAD_DIR="/app/uploads"
```

### 3. Reverse Proxy Setup (Nginx)

```nginx
# /etc/nginx/sites-available/rag-backend

upstream rag_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Proxy settings
    location / {
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/rag-backend /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## Scaling Considerations

### Horizontal Scaling

```bash
# 1. Load Balancer (AWS ALB)
aws elbv2 create-load-balancer \
  --name rag-backend-alb \
  --subnets subnet-12345678 subnet-87654321

# 2. Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name rag-backend-asg \
  --launch-template "LaunchTemplateName=rag-backend" \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3

# 3. Scaling Policies
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name rag-backend-asg \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration TargetValue=70.0,PredefinedMetricSpecification='{PredefinedMetricType=ASGAverageCPUUtilization}'
```

### Vertical Scaling

- Increase instance type (t3.medium → t3.large)
- Increase MongoDB cluster tier (M10 → M20)
- Increase memory allocation for embedding model

### Database Optimization

```javascript
// Create sharding key in MongoDB Atlas
db.chunks.createIndex({"document_id": "hashed"})

// Enable compression
// In MongoDB Atlas: Data Compression → Enable
```

---

## Monitoring and Logging

### Application Monitoring

```python
# app/utils/monitoring.py

from prometheus_client import Counter, Histogram, start_http_server
import time

request_count = Counter(
    'requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'request_duration_seconds',
    'HTTP request duration',
    ['endpoint']
)

# Middleware
from fastapi import Request

@app.middleware("http")
async def track_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    request_duration.labels(endpoint=request.url.path).observe(duration)
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response

# Start Prometheus metrics endpoint
start_http_server(8001)  # Metrics on port 8001
```

### Logging Setup

```python
# app/utils/logger.py

import logging
from pythonjsonlogger import jsonlogger

# JSON logging for production
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### CloudWatch Integration (AWS)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Configure
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/rag-backend.log",
            "log_group_name": "/rag/backend",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
EOF

# Start agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s
```

---

## Backup and Recovery

### MongoDB Backup

```bash
# Enable automated backups in MongoDB Atlas console
# Daily backups with 35-day retention

# Manual backup
mongobackup \
  --uri "mongodb+srv://user:pass@cluster.mongodb.net" \
  --out ./backups

# Restore from backup
mongorestore \
  --uri "mongodb+srv://user:pass@cluster.mongodb.net" \
  ./backups
```

### Application Backup

```bash
# Backup uploaded files
aws s3 sync app/uploads/ s3://backup-bucket/uploads/ --delete

# Backup code
git push origin main  # Already in version control

# Schedule with cron
0 2 * * * /usr/local/bin/backup-script.sh
```

### Disaster Recovery Plan

1. **Database Failure**:
   - MongoDB Atlas handles replication automatically
   - Restore from latest backup if needed

2. **Application Failure**:
   - Use auto-scaling to restart failed instances
   - Load balancer routes to healthy instances

3. **Data Loss**:
   - Point-in-time recovery from MongoDB backups
   - File backups in S3/Cloud Storage

---

## Rollback Procedure

### Version Control

```bash
# Tag releases
git tag -a v1.0.0 -m "Production release"
git push origin v1.0.0

# Deploy specific version
docker pull rag-backend:v1.0.0
docker run -d rag-backend:v1.0.0
```

### Database Migration Rollback

```bash
# If schema changed, have rollback script
python scripts/rollback_v1.py

# Or restore from pre-migration backup
mongorestore --uri "..." --backup-path ./pre-migration-backup
```

### Quick Rollback

```bash
# Kill failed deployment
docker stop rag-backend-new
docker rm rag-backend-new

# Restart previous version
docker start rag-backend-old
```

---

## Production Checklist - Final

- [ ] All environment variables configured
- [ ] Database backups working
- [ ] SSL/TLS certificates installed
- [ ] Monitoring and logging setup
- [ ] Auto-scaling policies configured
- [ ] Load balancer healthy
- [ ] Health checks passing
- [ ] DNS updated
- [ ] API keys rotated
- [ ] Documentation updated
- [ ] Team trained on deployment
- [ ] Incident response plan ready

---

## Support and Troubleshooting

### Common Issues

**High CPU Usage**:
```bash
# Check running processes
ps aux | grep uvicorn

# Increase instance size
# Or increase concurrency: uvicorn ... --workers 4
```

**Database Connection Timeout**:
```bash
# Check MongoDB Atlas IP whitelist
# Add server IP or enable public access temporarily

# Check network connectivity
curl -v "mongodb+srv://cluster.mongodb.net"
```

**Embedding Generation Slow**:
```bash
# Use faster embedding model
EMBEDDING_MODEL="all-MiniLM-L6-v2"  # Already optimal

# Or disable embedding cache temporarily
```

---

## References

- [MongoDB Atlas Deployment Guide](https://docs.mongodb.com/atlas/deployment/)
- [FastAPI Deployment Documentation](https://fastapi.tiangolo.com/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [AWS Deployment Guide](https://aws.amazon.com/getting-started/)

---

**Last Updated**: December 10, 2024
