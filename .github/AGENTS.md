# Backend AI Agent Instructions

You are working on the backend of a production-style RAG application.

==================================================
🎯 PROJECT PURPOSE
==================================================

Build a scalable FastAPI backend for a Retrieval-Augmented Generation (RAG) system.

Main data sources:
- CSV files (PRIMARY)
- Excel files (PRIMARY)
- PDF files (SECONDARY)

The system must support:
- dynamic uploads
- vector search
- semantic retrieval
- LLM-based responses

==================================================
🧠 TECH STACK
==================================================

Backend:
- Python
- FastAPI
- LangChain
- FAISS
- MongoDB
- Pandas
- PyPDF
- Groq API

==================================================
📂 ARCHITECTURE RULES
==================================================

Follow modular architecture.

Preferred structure:

app/
├── routes/
├── services/
├── rag/
├── utils/
├── vectorstore/
├── database/
├── uploads/
└── models/

Rules:
- Keep files small and reusable
- Avoid monolithic logic
- Separate business logic from routes
- Use service classes/functions
- Use reusable utility modules

==================================================
⚙️ API REQUIREMENTS
==================================================

Implement:
- POST /upload
- POST /query
- GET /documents
- GET /health

Use:
- Pydantic validation
- Proper HTTP status codes
- Structured JSON responses

==================================================
📊 CSV / EXCEL RULES
==================================================

CSV/Excel are PRIMARY RAG sources.

Convert structured rows into semantic text.

Example:
Input row:
| Employee | Sales | Month |

Converted semantic chunk:
"Employee Rohith achieved sales of 45000 in March."

Preserve:
- row relationships
- column meaning
- metadata

==================================================
📄 PDF RULES
==================================================

PDFs are SECONDARY context sources.

Implement:
- PDF extraction
- smart chunking
- overlap chunking
- metadata tracking

==================================================
🧠 RAG RULES
==================================================

Pipeline:
Query
→ Embedding
→ Similarity Search
→ Retrieval
→ Context Building
→ LLM Response

Requirements:
- use top-k retrieval
- prioritize CSV/Excel chunks
- avoid hallucination
- use strict prompts

Strict prompt:
"Answer ONLY using the provided context. If answer is unavailable, say you do not know based on uploaded data."

==================================================
🗄 DATABASE RULES
==================================================

MongoDB stores:
- uploaded file metadata
- chat history
- logs
- user records

FAISS stores:
- embeddings
- chunk vectors

Never confuse MongoDB with vector DB.

==================================================
🧹 CODING STANDARDS
==================================================

- Use type hints
- Add comments for important logic
- Use environment variables
- Add logging
- Add exception handling
- Avoid hardcoded values
- Write production-style code
- Keep functions reusable

==================================================
🚀 PERFORMANCE RULES
==================================================

- Avoid rebuilding full vector DB unnecessarily
- Support incremental uploads
- Use efficient retrieval
- Minimize repeated embedding generation

==================================================
🎯 GOAL
==================================================

Generate clean, scalable, beginner-friendly but production-style backend code for a modern RAG system.