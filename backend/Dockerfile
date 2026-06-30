# Multi-stage build for optimized Python backend
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install all Python dependencies into user space
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Final stage ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder (includes python-jose, bcrypt, and all others)
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application source
COPY . .

# Create necessary runtime directories
RUN mkdir -p uploads/files vectorstore/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
