# MongoDB Vector Search Configuration

## Overview

MongoDB Atlas Vector Search enables semantic search on embeddings. This guide explains how to set up and use vector search for your RAG system.

## Prerequisites

- MongoDB Atlas cluster (M10 or higher for production)
- Free tier (M0) works for development but with limited features
- Vector search requires M10+ for production use

## Creating a Vector Search Index

### Step 1: Access MongoDB Atlas Console

1. Go to [MongoDB Atlas](https://cloud.mongodb.com)
2. Log in to your account
3. Select your project
4. Select your cluster

### Step 2: Navigate to Search Indexes

1. Click on "Search" in the left sidebar
2. Click "Atlas Vector Search"
3. Click "Create Search Index"

### Step 3: Configure Index

**Option A: Using JSON Editor (Recommended)**

1. Click "JSON Editor"
2. Copy the following configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "similarity": "cosine"
    }
  ]
}
```

**Option B: Using UI**

1. Database: `rag_db`
2. Collection: `chunks`
3. Index Name: `vector_search_index`
4. Field: `embedding`
5. Similarity: `cosine`

### Step 4: Create Index

1. Click "Next"
2. Click "Create Search Index"
3. Wait for index to build (may take a few minutes)

**Status**: You can check status by going back to Search → Atlas Vector Search

## Vector Search Query Syntax

### Basic Vector Search

```javascript
db.chunks.aggregate([
  {
    "$search": {
      "cosmosSearch": false,
      "vectorSearch": {
        "vector": [0.1, -0.2, 0.3, ...],  // Your query embedding
        "k": 5                             // Number of results
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

### With Metadata Filtering

```javascript
db.chunks.aggregate([
  {
    "$search": {
      "cosmosSearch": false,
      "vectorSearch": {
        "vector": [0.1, -0.2, 0.3, ...],
        "k": 10  // Get more results before filtering
      },
      "returnStoredSource": true
    }
  },
  {
    "$match": {
      "metadata.source_priority": "primary"  // Filter by priority
    }
  },
  {
    "$project": {
      "chunk_text": 1,
      "source": 1,
      "similarity_score": {"$meta": "searchScore"},
      "metadata": 1
    }
  },
  {
    "$limit": 5  // Limit final results
  }
])
```

### With Multiple Filters

```javascript
db.chunks.aggregate([
  {
    "$search": {
      "cosmosSearch": false,
      "vectorSearch": {
        "vector": [0.1, -0.2, 0.3, ...],
        "k": 20
      },
      "returnStoredSource": true
    }
  },
  {
    "$match": {
      "metadata.file_type": "csv",
      "metadata.source_priority": "primary",
      "created_at": {
        "$gte": ISODate("2024-01-01")
      }
    }
  },
  {
    "$project": {
      "chunk_text": 1,
      "source": 1,
      "similarity_score": {"$meta": "searchScore"}
    }
  }
])
```

## Embedding Vector Size

**Important**: Your embedding vectors must match the configured dimensions:

- **Expected**: 384 dimensions (for all-MiniLM-L6-v2)
- **Each dimension**: Float (32-bit)
- **Total size**: ~1.5 KB per embedding

### Verify Vector Dimensions

```javascript
// Check first chunk embedding
db.chunks.findOne({}, {embedding: 1})

// In the output, count the array elements:
{
  _id: ObjectId(...),
  embedding: [0.123, -0.456, 0.789, ...]  // Should have 384 elements
}

// Count programmatically
db.chunks.aggregate([
  {$group: {_id: null, dim: {$first: {$size: "$embedding"}}}},
  {$project: {_id: 0, dimension: "$dim"}}
])
```

## Performance Tuning

### Optimal Search Parameters

```javascript
// Recommended for best results
{
  "vectorSearch": {
    "vector": [...],
    "k": 5          // Get top 5 results
  }
}
```

**Guidelines**:
- `k=3-5`: Fast, focused results
- `k=10`: Balanced results
- `k=20+`: Comprehensive, slower

### Index Optimization

```javascript
// Check index status
db.chunks.listSearchIndexes()

// Monitor index usage
db.chunks.aggregate([
  {$indexStats: {}}
])
```

## Similarity Metrics

### Cosine Similarity (Recommended)

- **Metric**: `cosine`
- **Range**: 0 to 1 (1 = identical, 0 = orthogonal)
- **Use case**: General semantic search
- **Speed**: Fast
- **Formula**: dot(A, B) / (||A|| * ||B||)

```javascript
// Cosine example
// Vector A: [1, 0, 0]
// Vector B: [1, 0, 0]
// Similarity: 1.0 (identical)

// Vector A: [1, 0, 0]
// Vector B: [0, 1, 0]
// Similarity: 0.0 (orthogonal)

// Vector A: [1, 0, 0]
// Vector B: [0.707, 0.707, 0]
// Similarity: 0.707 (45-degree angle)
```

### Other Similarity Options

- **Euclidean**: Measures distance in space (avoid for high dimensions)
- **Dot Product**: Similar to cosine but doesn't normalize
- **Hamming**: For binary vectors (not recommended for embeddings)

## Advanced Queries

### Hybrid Search (Vector + Text)

```javascript
db.chunks.aggregate([
  {
    "$search": {
      "cosmosSearch": true,  // Enable hybrid search
      "vectorSearch": {
        "vector": [0.1, -0.2, 0.3, ...],
        "k": 5
      },
      "text": {
        "query": "sales data",
        "path": "chunk_text"
      }
    }
  }
])
```

### Search with Aggregation

```javascript
db.chunks.aggregate([
  {
    "$search": {
      "vectorSearch": {
        "vector": [...],
        "k": 10
      }
    }
  },
  {
    "$addFields": {
      "similarity_percentage": {$multiply: ["$similarity_score", 100]}
    }
  },
  {
    "$match": {
      "similarity_percentage": {$gte: 50}
    }
  },
  {
    "$sort": {
      "similarity_score": -1
    }
  },
  {
    "$group": {
      "_id": "$source",
      "top_chunks": {$push: "$chunk_text"},
      "avg_score": {$avg: "$similarity_score"},
      "count": {$sum: 1}
    }
  }
])
```

## Common Issues

### "Vector Search Index Not Found"

**Problem**: Query returns error about missing index

**Solution**:
1. Go to MongoDB Atlas Console
2. Select your cluster
3. Click "Search" → "Atlas Vector Search"
4. Verify index is "READY" (not "BUILDING")
5. Try query again

### "Vector Dimension Mismatch"

**Problem**: Error about embedding dimensions

**Solution**:
```javascript
// Check your embedding dimensions
db.chunks.aggregate([
  {$group: {_id: null, dim: {$first: {$size: "$embedding"}}}},
  {$project: {_id: 0, dimension: "$dim"}}
])

// Expected: 384
// If different, regenerate embeddings with correct model
```

### "Too Many Results"

**Problem**: Query returns too many documents

**Solution**:
```javascript
// Reduce k value
{
  "vectorSearch": {
    "vector": [...],
    "k": 3  // Reduce from 10 to 3
  }
}

// Or add filtering
{
  "$match": {
    "metadata.source_priority": "primary"
  }
}
```

## Monitoring and Debugging

### Check Index Statistics

```javascript
db.chunks.aggregate([
  {$indexStats: {}}
])
```

### Verify Vector Search is Working

```javascript
// Simple test query
db.chunks.aggregate([
  {
    "$search": {
      "vectorSearch": {
        "vector": [0, 0, 0],  // Dummy vector
        "k": 1
      }
    }
  },
  {
    "$limit": 1
  }
])
```

### Performance Metrics

```javascript
// Time a query
var start = Date.now();
var result = db.chunks.aggregate([...]).toArray();
var time = Date.now() - start;
print("Query time: " + time + "ms");

// Check result count
print("Results: " + result.length);

// Check scores
result.forEach(r => print("Score: " + r.similarity_score));
```

## Best Practices

1. **Always normalize embeddings** before storing (Sentence-Transformers does this)
2. **Use appropriate k values** (3-10 for most queries)
3. **Filter before search** when possible (faster)
4. **Monitor index size** and query performance
5. **Update index** if schema changes
6. **Test queries** in MongoDB Shell first
7. **Use appropriate similarity** metric (cosine for embeddings)
8. **Backup regularly** (enable MongoDB backups)

## Example: Complete RAG Query

```javascript
// 1. Get query embedding (from your backend)
var queryEmbedding = [0.1, -0.2, 0.3, ...];  // 384 dimensions

// 2. Search in MongoDB
db.chunks.aggregate([
  {
    // Vector search
    "$search": {
      "cosmosSearch": false,
      "vectorSearch": {
        "vector": queryEmbedding,
        "k": 10
      }
    }
  },
  {
    // Filter by source priority
    "$match": {
      "metadata.source_priority": "primary"
    }
  },
  {
    // Format results
    "$project": {
      "chunk_text": 1,
      "source": 1,
      "score": {"$meta": "searchScore"},
      "metadata": 1
    }
  },
  {
    // Get top 5
    "$limit": 5
  },
  {
    // Sort by relevance
    "$sort": {"score": -1}
  }
])

// 3. Return results to your backend
// 4. Send to LLM with retrieved chunks
```

## References

- [MongoDB Vector Search Documentation](https://www.mongodb.com/docs/atlas/atlas-vector-search/overview/)
- [Aggregation Pipeline](https://www.mongodb.com/docs/manual/reference/operator/aggregation/)
- [Search Operators](https://www.mongodb.com/docs/atlas/atlas-search/operators-and-collectors/)

---

**Last Updated**: December 10, 2024
