# Backend Development Instructions

Backend Framework:
- FastAPI

Architecture Rules:
- Use modular services
- Separate routes, services, utils, rag pipeline
- Use async APIs where needed
- Use proper error handling

Folder Structure:
app/
├── routes/
├── services/
├── rag/
├── utils/
├── vectorstore/
├── uploads/

RAG Requirements:
- CSV/Excel are PRIMARY data sources
- PDFs are SECONDARY
- Use semantic chunking
- Use FAISS vector DB
- Use LangChain retriever
- Use Groq for generation

Prompt Rules:
- Prevent hallucination
- Use strict context-only answering

Coding Rules:
- Add type hints
- Add logging
- Add comments for important logic
- Avoid hardcoded paths
- Use environment variables

API Standards:
- REST APIs
- Proper response models
- Validation using Pydantic