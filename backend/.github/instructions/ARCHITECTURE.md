# System Architecture - MongoDB Atlas RAG

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│              Upload Panel │ Chat Panel │ Context Viewer         │
└──────────────────┬────────────────────────────────────────────┘
                   │ HTTP/REST API
┌──────────────────▼────────────────────────────────────────────┐
│                       FastAPI Backend                          │
│  ┌─────────────┬─────────────┬─────────────────────────────┐  │
│  │  Routes    │  Services   │  RAG Pipeline              │  │
│  │  /upload   │ file_svc    │  • Chunk                   │  │
│  │  /query    │ embed_svc   │  • Embed                   │  │
│  │  /documents│ vector_svc  │  • Store/Search            │  │
│  │  /health   │ rag_svc     │                            │  │
│  └─────────────┴─────────────┴──────────┬──────────────────┘  │
└──────────────────────────────┬───────────┘                     
                   │ Async / Motor Driver
┌──────────────────▼────────────────────────────────────────────┐
│           MongoDB Atlas Vector Store (Cloud)                   │
│  ┌──────────────────┐      ┌──────────────────────────────┐  │
│  │  documents col   │      │   chunks collection          │  │
│  │  • _id           │      │  • _id                       │  │
│  │  • filename      │      │  • document_id (ref)         │  │
│  │  • file_type     │      │  • chunk_text                │  │
│  │  • path          │      │  • embedding (384-dim)       │  │
│  │  • uploaded_at   │      │  • chunk_index               │  │
│  │                  │      │  • source                    │  │
│  │  [Indexes]       │      │  • metadata                  │  │
│  │  • filename      │      │  • created_at                │  │
│  │  • uploaded_at   │      │                              │  │
│  └──────────────────┘      │  [Indexes]                   │  │
│                            │  • document_id               │  │
│                            │  • source                    │  │
│                            │  • Vector Search Index       │  │
│                            │    (cosine similarity)       │  │
│                            └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
                        ┌───────────────────────┐
                        │  Groq LLM API         │
                        │  • llama-3.1-8b       │
                        │  • Strict RAG Prompt  │
                        └───────────────────────┘
```

## Component Architecture

### 1. API Layer (routes/)

**File**: `app/routes/rag_routes.py`

**Endpoints**:
- `POST /upload` - Upload and process files
- `POST /query` - Query documents with semantic search
- `GET /documents` - List all documents and statistics

**Responsibilities**:
- Request validation
- Response formatting
- Error handling
- Status code management

### 2. Service Layer (services/)

#### File Service
**File**: `app/services/file_service.py`

**Responsibilities**:
- Save uploaded files securely
- Parse CSV/XLSX/PDF
- Extract text content
- Return structured documents

#### Embedding Service
**File**: `app/services/embedding_service.py`

**Responsibilities**:
- Generate embeddings using Sentence-Transformers
- Batch embedding generation
- Cosine similarity calculation
- Cache embedding model

#### MongoDB Vector Service
**File**: `app/services/mongo_vector_service.py`

**Responsibilities**:
- Insert documents with embeddings
- Perform vector search queries
- Manage chunk operations
- Prioritize sources (primary/secondary)

#### RAG Service
**File**: `app/services/rag_service.py`

**Responsibilities**:
- Orchestrate upload pipeline
- Call file service → chunking → embedding → storage
- Orchestrate retrieval pipeline
- Manage statistics

### 3. Database Layer (db/)

#### MongoDB Connection
**File**: `app/db/mongo.py`

**Responsibilities**:
- Async connection lifecycle
- Connection pooling
- Index creation
- Error handling

#### Collections Manager
**File**: `app/db/collections.py`

**Responsibilities**:
- CRUD operations on documents collection
- CRUD operations on chunks collection
- Vector search queries
- Batch operations

### 4. RAG Pipeline (rag/)

#### Chunking Module
**File**: `app/rag/chunking.py`

**Responsibilities**:
- Convert CSV/XLSX rows to semantic text
- Split PDF text into chunks
- Handle overlapping chunks
- Preserve metadata

#### Generator Module
**File**: `app/rag/generator.py`

**Responsibilities**:
- Build prompts with context
- Call Groq LLM API
- Enforce strict RAG constraints
- Format responses

### 5. Main Application
**File**: `app/main.py`

**Responsibilities**:
- FastAPI app initialization
- Middleware setup (CORS)
- Startup events (MongoDB connection)
- Shutdown events (cleanup)

## Data Flow

### Upload Flow

```
1. User uploads file(s)
   ↓
2. API receives file(s) [POST /upload]
   ↓
3. File Service saves files locally
   ↓
4. File Service parses file content
   ├─ CSV → Semantic rows
   ├─ XLSX → Semantic rows per sheet
   └─ PDF → Text chunks by page
   ↓
5. Chunking module creates chunks with metadata
   ├─ Add source_priority: "primary" (CSV/XLSX)
   └─ Add source_priority: "secondary" (PDF)
   ↓
6. Embedding Service generates embeddings
   ├─ Batch processing for efficiency
   └─ 384-dimensional vectors
   ↓
7. MongoDB Vector Service stores:
   ├─ Document metadata → documents collection
   └─ Chunks with embeddings → chunks collection
   ↓
8. Response sent to user with statistics
```

### Query Flow

```
1. User asks question
   ↓
2. API receives query [POST /query]
   ↓
3. Embedding Service generates query embedding
   ↓
4. RAG Service retrieves chunks:
   ├─ MongoDB Vector Search (cosine similarity)
   ├─ Filter by metadata.source_priority: "primary" first
   └─ Add secondary if insufficient results
   ↓
5. Build context from top-k chunks
   ├─ Preserve source information
   └─ Format for LLM
   ↓
6. Generator calls Groq LLM with:
   ├─ System prompt (strict RAG instruction)
   ├─ User question
   └─ Retrieved context
   ↓
7. Process response:
   ├─ Extract answer
   ├─ Extract citations from metadata
   └─ Format output
   ↓
8. Response sent to user with:
   ├─ Answer from LLM
   ├─ Retrieved chunks (with scores)
   └─ Citations (source documents)
```

## Directory Structure

```
backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── db/                        # Database layer
│   │   ├── __init__.py
│   │   ├── mongo.py               # Connection & lifecycle
│   │   └── collections.py         # Collection managers
│   │
│   ├── routes/                    # API routes
│   │   ├── __init__.py
│   │   ├── rag_routes.py          # RAG endpoints
│   │   └── system_routes.py       # Health checks
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── file_service.py        # File operations
│   │   ├── embedding_service.py   # Embedding generation
│   │   ├── mongo_vector_service.py # Vector operations
│   │   └── rag_service.py         # Pipeline orchestration
│   │
│   ├── rag/                       # RAG pipeline
│   │   ├── __init__.py
│   │   ├── chunking.py            # Text chunking
│   │   ├── embeddings.py          # Embedding utilities
│   │   └── generator.py           # LLM integration
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic models
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings
│   │   └── logger.py              # Logging
│   │
│   ├── uploads/
│   │   └── files/                 # Uploaded files
│   │
│   └── vectorstore/
│       └── [deprecated - now using MongoDB]
│
├── .github/
│   ├── README.md                  # Documentation index
│   ├── guides/
│   │   ├── QUICK_START.md
│   │   ├── COMMANDS.md
│   │   └── SETUP_CHECKLIST.md
│   ├── mongodb/
│   │   ├── INTEGRATION.md
│   │   ├── SCHEMA.md
│   │   └── VECTOR_SEARCH.md
│   ├── instructions/
│   │   ├── ARCHITECTURE.md        # This file
│   │   ├── IMPLEMENTATION.md
│   │   ├── API_REFERENCE.md
│   │   └── rag.instructions.md
│   ├── workflows/
│   │   └── DEPLOYMENT.md
│   └── config/
│       └── .env.example
│
├── requirements.txt               # Python dependencies
├── verify.sh                       # Verification script
└── .env                           # Configuration (gitignored)
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Server** | FastAPI | Web framework |
| **ASGI** | Uvicorn | Application server |
| **Database** | MongoDB Atlas | Vector store |
| **Async** | Motor | Async MongoDB driver |
| **Embedding** | Sentence-Transformers | Embedding generation |
| **LLM** | Groq | AI responses |
| **Files** | Pandas, PyPDF | File parsing |
| **Config** | Pydantic Settings | Settings management |

## Key Design Decisions

### 1. MongoDB Atlas Over FAISS
**Why**:
- Scalability for multi-instance deployments
- Built-in replication and backups
- Vector search capabilities
- Cloud-hosted (no infrastructure)
- Better for production environments

### 2. Source Prioritization
**Why**:
- Business data (CSV/XLSX) is more structured and reliable
- PDFs are supplementary context
- Queries should prefer primary sources first
- If insufficient primary results, include secondary

### 3. Async Architecture
**Why**:
- Non-blocking I/O for better scalability
- Supports concurrent requests
- Better resource utilization
- Natural fit with FastAPI

### 4. Batch Embedding Generation
**Why**:
- More efficient than one-by-one
- Better GPU utilization (if available)
- Faster overall processing
- Better memory management

### 5. Sentence-Transformers for Embeddings
**Why**:
- Pre-trained models (no fine-tuning needed)
- Fast and lightweight
- 384-dimensional (good balance)
- Works offline (no API calls)
- Free and open-source

## Performance Considerations

### Bottlenecks
1. **Embedding Generation** - Most time-consuming step
   - Mitigation: Batch processing, caching model

2. **Vector Search** - Database lookup time
   - Mitigation: Proper indexing, top-k limit

3. **LLM API Call** - Network latency
   - Mitigation: Async calls, connection pooling

4. **File Parsing** - Large file processing
   - Mitigation: Streaming, chunking strategy

### Optimization Strategies
1. Use batch embedding whenever possible
2. Create proper indexes on MongoDB
3. Cache embedding model in memory
4. Limit top-k search results appropriately
5. Use connection pooling
6. Implement request caching

## Security Considerations

1. **File Upload**: Validate file types and sizes
2. **API Keys**: Store in environment variables
3. **MongoDB**: Use Atlas IP whitelist
4. **CORS**: Configure for frontend origin
5. **Logging**: Don't log sensitive data
6. **Rate Limiting**: Implement if needed

## Scalability

### Horizontal Scaling
- Multiple FastAPI instances behind load balancer
- MongoDB handles distribution (sharding)
- Stateless services

### Vertical Scaling
- Increase embedding model caching
- Optimize chunk size
- Increase top-k limits

## Monitoring & Observability

### Key Metrics
1. Upload processing time
2. Query latency (embedding + search + LLM)
3. Vector search hit rate
4. MongoDB query performance
5. Memory usage
6. API endpoint latency

### Logging
- Backend logs all operations
- MongoDB query logs
- LLM API response logs
- Error tracking

---

**Last Updated**: December 10, 2024
