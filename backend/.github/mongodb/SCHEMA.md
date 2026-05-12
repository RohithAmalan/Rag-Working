# MongoDB Collections Schema

## Overview

This document describes the MongoDB collections used in the RAG system for storing documents, chunks, and embeddings.

## collections

### documents Collection

Stores metadata about uploaded files.

**Schema**:
```json
{
  "_id": ObjectId,
  "filename": String,
  "file_type": String,
  "path": String,
  "uploaded_at": ISODate
}
```

**Example**:
```json
{
  "_id": ObjectId("65a1b2c3d4e5f6g7h8i9j0k1"),
  "filename": "sales_report.csv",
  "file_type": "csv",
  "path": "app/uploads/files/abc123_sales_report.csv",
  "uploaded_at": ISODate("2024-12-10T10:30:00Z")
}
```

**Indexes**:
```javascript
db.documents.createIndex({filename: 1})
db.documents.createIndex({uploaded_at: -1})
```

**Use Cases**:
- List all uploaded documents
- Track file metadata
- Retrieve document details by filename
- Sort documents by upload date

---

### chunks Collection

Stores document chunks with embedding vectors for semantic search.

**Schema**:
```json
{
  "_id": ObjectId,
  "document_id": ObjectId,
  "chunk_text": String,
  "embedding": Array<Float>,
  "chunk_index": Number,
  "source": String,
  "metadata": Object,
  "created_at": ISODate
}
```

**Detailed Field Descriptions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `_id` | ObjectId | Unique chunk identifier | ObjectId(...) |
| `document_id` | ObjectId | Reference to parent document | ObjectId(...) |
| `chunk_text` | String | Actual text content | "Business data showing..." |
| `embedding` | Array<Float> | 384-dimensional embedding vector | [0.123, -0.456, ...] |
| `chunk_index` | Number | Sequential chunk number | 0, 1, 2, ... |
| `source` | String | Source file name | "report.pdf" |
| `metadata` | Object | Additional metadata | See below |
| `created_at` | ISODate | Creation timestamp | ISODate("2024-12-10...") |

**Metadata Schema**:
```json
{
  "file_type": String,        // "csv", "xlsx", "pdf"
  "source_priority": String,  // "primary" or "secondary"
  "sheet_name": String,       // For Excel files (optional)
  "row_index": Number,        // For CSV/Excel (optional)
  "page_index": Number        // For PDF (optional)
}
```

**Complete Example**:
```json
{
  "_id": ObjectId("65a1b2c3d4e5f6g7h8i9j0k2"),
  "document_id": ObjectId("65a1b2c3d4e5f6g7h8i9j0k1"),
  "chunk_text": "Business data row from sales_report.csv. This record shows Product is Laptop, Sales is 5000, Month is March. Raw row mapping: Product=Laptop | Sales=5000 | Month=March.",
  "embedding": [0.123, -0.456, 0.789, ..., 0.234],  // 384 dimensions
  "chunk_index": 0,
  "source": "sales_report.csv",
  "metadata": {
    "file_type": "csv",
    "source_priority": "primary",
    "sheet_name": null,
    "row_index": 0
  },
  "created_at": ISODate("2024-12-10T10:30:05Z")
}
```

**Indexes**:
```javascript
// Basic indexes
db.chunks.createIndex({document_id: 1})
db.chunks.createIndex({source: 1})

// Vector search index (for Atlas Vector Search)
db.chunks.createSearchIndex({
  name: "vector_search_index",
  type: "vectorSearch",
  definition: {
    fields: [
      {
        type: "vector",
        path: "embedding",
        similarity: "cosine"
      }
    ]
  }
})
```

**Use Cases**:
- Vector similarity search
- Retrieve chunks by document
- Filter chunks by source
- Find all chunks with specific metadata

---

## Queries

### Common Query Examples

#### 1. Vector Similarity Search
```javascript
// Find top 5 most similar chunks to a query embedding
db.chunks.aggregate([
  {
    "$search": {
      "vectorSearch": {
        "vector": [0.1, -0.2, 0.3, ...],  // Query embedding
        "k": 5
      },
      "returnStoredSource": true
    }
  },
  {
    "$project": {
      "chunk_text": 1,
      "source": 1,
      "similarity_score": {"$meta": "searchScore"},
      "metadata": 1
    }
  }
])
```

#### 2. Get All Chunks for a Document
```javascript
db.chunks.find({document_id: ObjectId("...")})
  .sort({chunk_index: 1})
```

#### 3. Filter by Priority
```javascript
db.chunks.find({"metadata.source_priority": "primary"})
  .limit(10)
```

#### 4. Count Chunks by Source
```javascript
db.chunks.aggregate([
  {$group: {_id: "$source", count: {$sum: 1}}},
  {$sort: {count: -1}}
])
```

#### 5. Find CSV Data (Business Data)
```javascript
db.chunks.find({"metadata.file_type": "csv"})
```

#### 6. Find PDF Chunks
```javascript
db.chunks.find({"metadata.file_type": "pdf"})
```

#### 7. Get Document with All Chunks
```javascript
db.chunks.aggregate([
  {$match: {document_id: ObjectId("...")}},
  {$lookup: {
    from: "documents",
    localField: "document_id",
    foreignField: "_id",
    as: "document"
  }},
  {$unwind: "$document"},
  {$sort: {chunk_index: 1}}
])
```

#### 8. Statistics
```javascript
// Total chunks
db.chunks.countDocuments()

// Total documents
db.documents.countDocuments()

// Chunks by file type
db.chunks.aggregate([
  {$group: {_id: "$metadata.file_type", count: {$sum: 1}}}
])

// Average chunks per document
db.chunks.aggregate([
  {$group: {_id: "$document_id", count: {$sum: 1}}},
  {$group: {_id: null, avg_chunks: {$avg: "$count"}}}
])
```

---

## Data Size Estimates

### Embedding Vector Size
```
384 dimensions × 4 bytes (float32) = 1,536 bytes per embedding
```

### Typical Document Sizes

| File Type | Typical Size | Chunks | Total Size |
|-----------|--------------|--------|-----------|
| CSV (100 rows) | 5 KB | 100 | ~154 KB |
| Excel (1000 rows) | 50 KB | 1000 | ~1.5 MB |
| PDF (10 pages) | 500 KB | 50 | ~77 KB |

### Estimated Storage (1000 files)

| Scenario | Documents | Chunks | Storage |
|----------|-----------|--------|---------|
| All CSV | 1000 | 100k | ~150 MB |
| All Excel | 1000 | 100k | ~150 MB |
| All PDF | 1000 | 50k | ~77 MB |
| Mixed | 1000 | 75k | ~115 MB |

---

## Maintenance

### Backup Strategy

```bash
# Export collections
mongoexport --uri "mongodb+srv://..." \
  --collection documents \
  --out documents_backup.json

mongoexport --uri "mongodb+srv://..." \
  --collection chunks \
  --out chunks_backup.json
```

### Cleanup Old Chunks

```javascript
// Delete chunks older than 30 days
db.chunks.deleteMany({
  created_at: {$lt: new Date(Date.now() - 30*24*60*60*1000)}
})
```

### Reindex After Large Deletion

```javascript
db.chunks.reIndex()
db.documents.reIndex()
```

---

## Performance Considerations

### Indexing Strategy
1. **Always index** `document_id` and `source` for fast lookups
2. **Create vector search index** for similarity search
3. **Consider indexing** metadata fields if frequently filtered

### Query Optimization
1. Use vector search for semantic queries (not text search)
2. Filter by `metadata.source_priority` to limit results
3. Use `top_k` parameter to limit returned chunks
4. Enable MongoDB compression for network efficiency

### Storage Optimization
1. Embeddings are stored as Arrays of Float32
2. Each 384-dim embedding ≈ 1.5 KB
3. MongoDB stores documents efficiently with compression
4. Consider Archive Storage for very old data

---

## Validation

### Collection Validation Rules

```javascript
// Optional: Add validation rules
db.createCollection("chunks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["document_id", "chunk_text", "embedding", "chunk_index", "source"],
      properties: {
        _id: { bsonType: "objectId" },
        document_id: { bsonType: "objectId" },
        chunk_text: { bsonType: "string" },
        embedding: { 
          bsonType: "array",
          items: { bsonType: "double" }
        },
        chunk_index: { bsonType: "int" },
        source: { bsonType: "string" },
        metadata: { bsonType: "object" },
        created_at: { bsonType: "date" }
      }
    }
  }
})
```

---

## Migration from FAISS

When migrating from FAISS:

1. **Export FAISS vectors** to JSON
2. **Create documents** from file metadata
3. **Create chunks** with embeddings
4. **Verify** counts match original
5. **Test** vector search queries
6. **Cleanup** old FAISS files

---

**Last Updated**: December 10, 2024
