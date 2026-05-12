# RAG Pipeline Instructions

Pipeline Flow:
User Query
→ Embedding
→ Similarity Search
→ Retrieval
→ Context Building
→ LLM Generation

Important Rules:
- CSV/Excel are priority retrieval sources
- PDF chunks are secondary
- Use chunk overlap
- Preserve structured row relationships

Embedding Rules:
- Use OpenAI embeddings OR local fallback
- Ensure query and document embeddings use same model

Retrieval Rules:
- Use top-k retrieval
- Prioritize relevance scoring
- Avoid hallucination

Generation Rules:
- Use strict prompts
- Answer ONLY from retrieved context
- If context missing, say:
  "I don't know based on uploaded data."