# LangGraph Integration - Phase 1 Complete ✅

## What Was Implemented

Phase 1 of the LangGraph integration is now complete! This adds a stateful workflow orchestration layer to the existing RAG system using LangGraph.

### Files Created

1. **`backend/app/rag/langgraph_state.py`**
   - Defines `AgentState` TypedDict with workflow state schema
   - Includes fields for: question, query intent, retrieved chunks, answer, citations, confidence, metadata
   - Prepared for future phases (MultiStepState, ConversationState)

2. **`backend/app/rag/langgraph_nodes.py`**
   - **analyze_query_node**: Analyzes query intent (exact_lookup, ranking, aggregation, general)
   - **retrieve_node**: Wraps existing mongo_vector_service hybrid search
   - **generate_node**: Generates answers using existing generator with citations and confidence

3. **`backend/app/rag/langgraph_pipeline.py`**
   - **build_basic_rag_graph()**: Creates linear workflow (analyze → retrieve → generate)
   - Prepared for Phase 2 conditional routing
   - Prepared for Phase 3 multi-agent workflows

4. **`backend/app/services/langgraph_rag_service.py`**
   - **LangGraphRAGService**: Orchestrates LangGraph workflow execution
   - Returns enhanced responses with confidence scores and metadata

5. **Updated `backend/app/services/rag_service.py`**
   - Added `query_with_langgraph()` method
   - Initializes LangGraphRAGService in constructor
   - Maintains backward compatibility with existing `search_and_retrieve()`

6. **Updated `backend/app/routes/rag_routes.py`**
   - Added new **POST /query-langgraph** endpoint
   - Existing **POST /query** endpoint unchanged (backward compatible)

### Dependencies Added

```txt
langgraph==1.2.0
langgraph-checkpoint==4.1.0
```

## Current Workflow

### Linear Flow (Phase 1)

```
User Query
    ↓
analyze_query_node
    ↓
retrieve_node (MongoDB vector search)
    ↓
generate_node (Answer + Citations)
    ↓
Response with confidence & metadata
```

### What Each Node Does

#### 1. analyze_query_node
- Extracts entities (IDs, phones, emails, names)
- Detects ranking intent (top-k, highest, lowest, etc.)
- Detects exact match requirements
- Classifies intent: `exact_lookup`, `ranking`, `aggregation`, `general`

#### 2. retrieve_node
- Uses existing `mongo_vector_service.search_chunks()`
- Hybrid search: exact match + vector similarity + ranking
- Returns chunks with similarity scores
- Tracks retrieval strategy used

#### 3. generate_node
- Uses existing `generate_answer()` function
- Builds citations from chunk metadata
- Calculates confidence score based on similarity scores
- Returns structured answer with metadata

## API Endpoints

### New Endpoint: POST /query-langgraph

```bash
curl -X POST http://localhost:8000/query-langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me top 3 unit prices",
    "top_k": 15,
    "selected_file": "Customer-Purchase-History.xlsx"
  }'
```

**Response:**
```json
{
  "answer": "Based on the data...",
  "retrieved_chunks": [...],
  "citations": [
    {
      "file_name": "Customer-Purchase-History.xlsx",
      "source_type": "primary",
      "sheet_name": "Sheet1",
      "row_index": 5,
      "chunk_index": 10
    }
  ],
  "confidence": 0.92,
  "metadata": {
    "query_intent": "ranking",
    "retrieval_strategy": "ranking",
    "workflow_path": ["analyze_query", "retrieve", "generate"],
    "requires_ranking": true,
    "requires_exact_match": false,
    "errors": []
  }
}
```

### Existing Endpoint: POST /query (unchanged)

The legacy endpoint still works for backward compatibility.

## Testing Phase 1

### 1. Start the Server

```bash
cd /Users/rohith/RAG/backend
./start_server.sh
```

### 2. Test LangGraph Endpoint

```bash
# Test ranking query
curl -X POST http://localhost:8000/query-langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show highest unit price",
    "top_k": 10,
    "selected_file": null
  }'

# Test exact lookup
curl -X POST http://localhost:8000/query-langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Find customer ID C001",
    "top_k": 5,
    "selected_file": null
  }'

# Test general query
curl -X POST http://localhost:8000/query-langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products are available?",
    "top_k": 10,
    "selected_file": null
  }'
```

### 3. Check Logs

Look for these startup logs:
```
INFO | app.rag.langgraph_pipeline | Building Phase 1 LangGraph RAG workflow (linear)
INFO | app.rag.langgraph_pipeline | Phase 1 workflow compiled successfully
INFO | app.services.langgraph_rag_service | LangGraph RAG service initialized
INFO | app.services.rag_service | RagService initialized with LangGraph support
```

During query execution:
```
INFO | app.services.langgraph_rag_service | LangGraph query: Show highest unit price... (file=None, top_k=10)
INFO | app.rag.langgraph_nodes | Query analysis: intent=ranking, ranking=True, exact=False
INFO | app.rag.langgraph_nodes | Retrieved 15 chunks using strategy: ranking
INFO | app.rag.langgraph_nodes | Generated answer with confidence: 0.92
INFO | app.services.langgraph_rag_service | LangGraph completed: confidence=0.92, chunks=15, path=['analyze_query', 'retrieve', 'generate']
```

## What's New in Phase 1

✅ **State Management**: Workflow state tracked through LangGraph TypedDict
✅ **Intent Classification**: Automatic query intent detection
✅ **Confidence Scoring**: Answers include confidence metrics
✅ **Workflow Tracking**: Each response shows which nodes were executed
✅ **Error Handling**: Errors tracked in state and returned in metadata
✅ **Backward Compatible**: Existing /query endpoint unchanged

## Benefits

1. **Observability**: Full visibility into workflow execution path
2. **Extensibility**: Easy to add new nodes and routing logic in future phases
3. **Testability**: Each node can be tested independently
4. **Confidence**: Users see answer confidence scores
5. **Metadata**: Rich debugging information in responses

## Next Phases (Coming Soon)

### Phase 2: Advanced Routing (2-3 days)
- Conditional routing based on query intent
- Specialized retrieval nodes for exact/ranking/aggregation
- Query refinement based on intent

### Phase 3: Multi-Agent (3-5 days)
- Complex query decomposition
- Parallel file retrieval
- Cross-file comparisons
- Result aggregation

### Phase 4: Memory & Learning (Optional)
- Conversation history
- Query refinement based on feedback
- Self-correction loops

## Frontend Integration (Optional)

To use the new endpoint from the frontend, update `frontend/src/services/api.js`:

```javascript
export const queryDocumentsLangGraph = async (question, selectedFile = null, topK = 15) => {
  const response = await fetch(`${API_BASE}/query-langgraph`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      selected_file: selectedFile,
      top_k: topK,
    }),
  });
  
  if (!response.ok) throw new Error('LangGraph query failed');
  return response.json();
};
```

Then in `ChatPanel.jsx`, switch from `/query` to `/query-langgraph` and display confidence + metadata.

---

## Server Status

✅ **Server Running**: http://0.0.0.0:8000
✅ **Endpoints**:
- POST /query (legacy)
- POST /query-langgraph ⭐ NEW
- POST /upload
- GET /documents
- GET /health

✅ **Vector Store**: 4353 chunks, 6 documents, MongoDB backend
✅ **LangGraph**: Phase 1 workflow initialized

## Summary

Phase 1 is **complete and operational**. The basic LangGraph workflow is now integrated into the RAG system, providing stateful orchestration, intent classification, and enhanced response metadata. The system is backward compatible and ready for Phase 2 enhancements.
