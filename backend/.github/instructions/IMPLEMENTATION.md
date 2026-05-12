# Implementation Details

## Code Organization and Patterns

### 1. Service Layer Pattern

All business logic is organized in service classes for testability and reusability.

#### Example: Embedding Service

```python
# app/services/embedding_service.py

from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingService:
    _model = None
    
    @staticmethod
    def get_embedding_model():
        """Lazy load and cache embedding model"""
        if EmbeddingService._model is None:
            EmbeddingService._model = SentenceTransformer("all-MiniLM-L6-v2")
        return EmbeddingService._model
    
    @staticmethod
    def generate_embeddings(texts):
        """Generate embeddings for single or multiple texts"""
        model = EmbeddingService.get_embedding_model()
        if isinstance(texts, str):
            texts = [texts]
        embeddings = model.encode(texts)
        return embeddings.tolist()
    
    @staticmethod
    def compute_similarity(vector1, vector2):
        """Cosine similarity between two vectors"""
        v1 = np.array(vector1)
        v2 = np.array(vector2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
```

**Key Patterns**:
- Lazy loading model with static class variable
- Support both single string and list inputs
- Batch processing capabilities
- Type annotations

### 2. Async Database Layer

All database operations are async using Motor driver.

#### Example: MongoDB Collections

```python
# app/db/collections.py

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

class DocumentsCollection:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["documents"]
    
    async def insert_document(self, document_data):
        """Insert new document"""
        result = await self.collection.insert_one(document_data)
        return result.inserted_id
    
    async def get_document(self, doc_id):
        """Retrieve document by ID"""
        return await self.collection.find_one({"_id": doc_id})
    
    async def delete_document(self, doc_id):
        """Delete document and related chunks"""
        result = await self.collection.delete_one({"_id": doc_id})
        return result.deleted_count


class ChunksCollection:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["chunks"]
    
    async def vector_search(self, query_embedding, k=5, source_priority=None):
        """
        Perform vector similarity search
        
        Args:
            query_embedding: 384-dimensional embedding vector
            k: Number of results to return
            source_priority: Filter by 'primary' or 'secondary' (optional)
        """
        pipeline = [
            {
                "$search": {
                    "cosmosSearch": False,
                    "vectorSearch": {
                        "vector": query_embedding,
                        "k": k
                    },
                    "returnStoredSource": True
                }
            }
        ]
        
        if source_priority:
            pipeline.append({
                "$match": {
                    "metadata.source_priority": source_priority
                }
            })
        
        pipeline.append({
            "$project": {
                "chunk_text": 1,
                "source": 1,
                "similarity_score": {"$meta": "searchScore"},
                "metadata": 1
            }
        })
        
        results = []
        async for doc in self.collection.aggregate(pipeline):
            results.append(doc)
        
        return results
    
    async def insert_chunks_batch(self, chunks):
        """Batch insert chunks"""
        result = await self.collection.insert_many(chunks)
        return result.inserted_ids
```

**Key Patterns**:
- Async/await throughout
- Type hints for IDE support
- Pipeline-based queries
- Batch operations

### 3. RAG Pipeline Orchestration

#### Example: File Upload Processing

```python
# app/services/rag_service.py

from app.services.file_service import FileService
from app.rag.chunking import create_chunks
from app.services.embedding_service import EmbeddingService
from app.services.mongo_vector_service import MongoVectorService

class RagService:
    def __init__(self, mongo_vector_service: MongoVectorService):
        self.vector_service = mongo_vector_service
    
    async def upload_and_process_files(self, uploaded_files):
        """
        Complete upload pipeline:
        Upload → Parse → Chunk → Embed → Store
        """
        all_documents = []
        all_chunks = []
        errors = []
        
        for file in uploaded_files:
            try:
                # 1. Save file
                file_path = FileService.save_file(file)
                
                # 2. Extract and parse
                file_type = FileService.get_file_type(file.filename)
                documents = FileService.extract_from_file(file_path, file_type)
                
                # 3. Create chunks with metadata
                chunks = create_chunks(documents, file.filename, file_type)
                
                # 4. Generate embeddings
                texts = [chunk['chunk_text'] for chunk in chunks]
                embeddings = EmbeddingService.generate_embeddings(texts)
                
                # 5. Add embeddings to chunks
                for chunk, embedding in zip(chunks, embeddings):
                    chunk['embedding'] = embedding
                
                # 6. Store in MongoDB
                doc_id = await self.vector_service.store_document(
                    filename=file.filename,
                    file_type=file_type,
                    path=file_path
                )
                
                await self.vector_service.store_chunks_batch(chunks, doc_id)
                
                all_documents.append({
                    "filename": file.filename,
                    "chunks": len(chunks),
                    "status": "success"
                })
                
            except Exception as e:
                errors.append({"filename": file.filename, "error": str(e)})
        
        return {
            "message": "Processing complete",
            "documents": all_documents,
            "errors": errors
        }
```

**Key Patterns**:
- Each step is separate function/method
- Error handling at each stage
- Type hints
- Async operations

### 4. API Route Handlers

#### Example: Query Endpoint

```python
# app/routes/rag_routes.py

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["rag"])

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

@router.post("/query")
async def query_documents(request: QueryRequest):
    """
    Query documents with semantic search
    
    Args:
        question: User question
        top_k: Number of chunks to retrieve
    
    Returns:
        Answer from LLM with retrieved chunks and citations
    """
    try:
        rag_service = request.app.state.rag_service
        
        # 1. Generate embedding for question
        query_embedding = EmbeddingService.generate_embeddings(request.question)
        
        # 2. Search in vector store
        retrieved_chunks = await rag_service.search_and_retrieve(
            query_embedding=query_embedding,
            top_k=request.top_k
        )
        
        if not retrieved_chunks:
            return {
                "answer": "No relevant documents found.",
                "retrieved_chunks": [],
                "citations": []
            }
        
        # 3. Build context
        context = "\n".join([c['chunk_text'] for c in retrieved_chunks])
        
        # 4. Generate response from LLM
        from app.rag.generator import generate_rag_response
        answer = generate_rag_response(question=request.question, context=context)
        
        # 5. Format response
        return {
            "answer": answer,
            "retrieved_chunks": retrieved_chunks,
            "citations": [c['source'] for c in retrieved_chunks]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Key Patterns**:
- Pydantic models for validation
- Type hints
- Error handling with HTTPException
- Structured response format

### 5. Chunking Strategy

#### Example: CSV to Semantic Chunks

```python
# app/rag/chunking.py

import pandas as pd

def create_chunks_from_csv(file_path, filename):
    """
    Convert CSV rows to semantic text chunks
    
    Example:
        Input CSV: | Product | Sales | Month |
                   | Laptop  | 5000  | March |
        
        Output: "Product is Laptop, Sales is 5000, Month is March"
    """
    df = pd.read_csv(file_path)
    chunks = []
    
    for idx, row in df.iterrows():
        # Convert row to semantic text
        row_text = " ".join([f"{col} is {row[col]}" for col in df.columns])
        
        chunk = {
            'chunk_text': row_text,
            'chunk_index': idx,
            'source': filename,
            'metadata': {
                'file_type': 'csv',
                'source_priority': 'primary',  # CSV is primary source
                'row_index': idx
            }
        }
        chunks.append(chunk)
    
    return chunks


def create_chunks_from_pdf(text_content, filename, chunk_size=500, overlap=50):
    """
    Split PDF text into overlapping chunks
    
    Args:
        text_content: Extracted PDF text
        filename: Source filename
        chunk_size: Size of each chunk in characters
        overlap: Overlap between consecutive chunks
    """
    chunks = []
    words = text_content.split()
    chunk_index = 0
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        
        chunk = {
            'chunk_text': chunk_text,
            'chunk_index': chunk_index,
            'source': filename,
            'metadata': {
                'file_type': 'pdf',
                'source_priority': 'secondary',  # PDF is secondary
                'page_index': chunk_index
            }
        }
        chunks.append(chunk)
        chunk_index += 1
    
    return chunks
```

**Key Patterns**:
- Source-specific logic
- Metadata preservation
- Semantic text generation
- Configurable chunk size

### 6. LLM Integration (Groq)

#### Example: Response Generation

```python
# app/rag/generator.py

from groq import Groq
from app.utils.config import settings

def generate_rag_response(question: str, context: str) -> str:
    """
    Generate LLM response using strict RAG prompt
    
    Args:
        question: User question
        context: Retrieved context from vector search
    
    Returns:
        LLM-generated answer
    """
    client = Groq(api_key=settings.groq_api_key)
    
    system_prompt = """You are a helpful assistant answering questions based ONLY on the provided context.

IMPORTANT RULES:
1. Answer ONLY using the provided context
2. If the answer is not in the context, say "I don't know based on the provided data"
3. Do NOT make up or infer information not in the context
4. Always cite the source when using the context
5. Be concise and accurate"""
    
    user_prompt = f"""Context:
{context}

Question: {question}

Answer:"""
    
    response = client.messages.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_tokens=1024,
        temperature=0.3  # Lower temperature for factual answers
    )
    
    return response.choices[0].message.content
```

**Key Patterns**:
- Strict system prompt to prevent hallucination
- Structured messages format
- Temperature set for factual responses
- Error handling implicit (Groq raises on API errors)

## Testing Patterns

### Unit Test Example

```python
# tests/test_embedding_service.py

import pytest
from app.services.embedding_service import EmbeddingService

@pytest.mark.asyncio
async def test_generate_embeddings_single():
    """Test single text embedding"""
    text = "Hello world"
    embedding = EmbeddingService.generate_embeddings(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.asyncio
async def test_generate_embeddings_batch():
    """Test batch text embedding"""
    texts = ["Hello world", "Goodbye world"]
    embeddings = EmbeddingService.generate_embeddings(texts)
    
    assert len(embeddings) == 2
    assert all(len(e) == 384 for e in embeddings)

def test_cosine_similarity():
    """Test similarity calculation"""
    v1 = [1, 0, 0]
    v2 = [1, 0, 0]
    
    similarity = EmbeddingService.compute_similarity(v1, v2)
    assert abs(similarity - 1.0) < 0.01  # Nearly identical
```

## Database Initialization Pattern

### Startup Event

```python
# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.services.rag_service import RagService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    db = get_database()
    app.state.rag_service = RagService(db)
    
    yield
    
    # Shutdown
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)
```

## Error Handling Pattern

```python
# app/utils/exceptions.py

class RAGException(Exception):
    """Base exception for RAG system"""
    pass

class FileProcessingError(RAGException):
    """Raised when file processing fails"""
    pass

class EmbeddingError(RAGException):
    """Raised when embedding generation fails"""
    pass

class VectorSearchError(RAGException):
    """Raised when vector search fails"""
    pass

class LLMError(RAGException):
    """Raised when LLM call fails"""
    pass

# Usage
try:
    embeddings = generate_embeddings(texts)
except Exception as e:
    raise EmbeddingError(f"Failed to generate embeddings: {str(e)}")
```

## Configuration Pattern

```python
# app/utils/config.py

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "rag_db"
    documents_collection: str = "documents"
    chunks_collection: str = "chunks"
    
    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    batch_size: int = 32
    
    # LLM
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    
    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Search
    top_k_default: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Logging Pattern

```python
# app/utils/logger.py

import logging

def get_logger(name):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

# Usage
logger = get_logger(__name__)
logger.info("Processing file: %s", filename)
logger.error("Error: %s", str(e))
```

---

**Last Updated**: December 10, 2024
