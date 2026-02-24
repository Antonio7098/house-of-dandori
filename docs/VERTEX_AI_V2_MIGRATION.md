# Vertex AI Vector Search V2 Migration Guide

This guide explains how to migrate from Vertex AI Vector Search V1 (Index/Endpoint) to V2 (Collections).

## Overview

Vector Search 2.0 introduces Collections, which provide a unified data model that stores vectors, metadata, and content together. This is simpler and more efficient than the V1 approach of separate Indexes, Endpoints, and document storage.

## Key Differences

| Feature | V1 (Index/Endpoint) | V2 (Collections) |
|---------|---------------------|------------------|
| **Storage** | Index + Endpoint + separate docs | Collection (unified) |
| **Setup** | Create Index, deploy to Endpoint | Create Collection |
| **Filtering** | Namespace objects | Dict-based query syntax |
| **Schema** | Separate configuration | Unified in Collection |
| **Filterable Fields** | Any metadata | Must be defined in schema |

## Migration Steps

### 1. Create a Collection

Run the provided script to create a V2 collection:

```bash
python scripts/create_vertex_collection.py
```

Or create manually:

```python
from google.cloud import vectorsearch_v1beta

PROJECT_ID = "your-project-id"
LOCATION = "europe-west2"
COLLECTION_ID = "dandori-courses-collection"

client = vectorsearch_v1beta.VectorSearchServiceClient()

request = vectorsearch_v1beta.CreateCollectionRequest(
    parent=f"projects/{PROJECT_ID}/locations/{LOCATION}",
    collection_id=COLLECTION_ID,
    collection={
        "display_name": "Dandori Courses Collection",
        "description": "Course search with semantic matching and filtering",
        "data_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "number"},
                "course_type": {"type": "string"},
                "location": {"type": "string"},
                "instructor": {"type": "string"},
                "cost": {"type": "string"},
                "page_content": {"type": "string"},
            },
        },
        "vector_schema": {
            "embedding": {
                "dense_vector": {
                    "dimensions": 768  # For text-embedding-005
                }
            },
        },
    },
)

operation = client.create_collection(request=request)
result = operation.result()
print(f"Collection created: {result.name}")
```

### 2. Update Environment Variables

Update your `.env` file:

```bash
# Old V1 settings (remove or comment out)
# VERTEX_AI_INDEX_ID=your-index-id
# VERTEX_AI_INDEX_ENDPOINT_ID=your-endpoint-id

# New V2 settings
VERTEX_AI_API_VERSION=v2
VERTEX_AI_COLLECTION_ID=dandori-courses-collection
```

### 3. Update Code (if using custom implementations)

The `VertexAIVectorSearchProvider` class automatically handles both V1 and V2 APIs based on the `api_version` parameter. No code changes needed if using the standard provider.

#### Filtering Syntax Changes

**V1 (old):**
```python
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace

filters = [Namespace(name="location", allow_tokens=["London"])]
results = vector_store.query(query_texts=["courses"], filter=filters)
```

**V2 (new):**
```python
# Simple equality
filter_dict = {"location": {"$eq": "London"}}

# Multiple conditions with AND
filter_dict = {
    "$and": [
        {"location": {"$eq": "London"}},
        {"cost": {"$lt": "50"}}
    ]
}

# OR conditions
filter_dict = {
    "$or": [
        {"location": {"$eq": "London"}},
        {"location": {"$eq": "Manchester"}}
    ]
}

results = vector_store.query(query_texts=["courses"], filter_dict=filter_dict)
```

### 4. Reindex Your Data

After creating the collection, reindex your courses:

```bash
curl -X POST http://localhost:5000/api/index
```

Or programmatically:

```python
from src.services.rag_service import get_rag_service
from src.models.database import get_db_connection
from src.core.utils import parse_json_fields

# Get courses from database
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM courses")
courses = [parse_json_fields(c) for c in cursor.fetchall()]
conn.close()

# Index in V2 collection
rag = get_rag_service()
rag.index_courses(courses)
```

### 5. Test the Migration

Test that search works with the new collection:

```bash
# Basic search
curl "http://localhost:5000/api/search?q=waffle+weaving&n=5"

# Search with filters (if your API supports it)
curl -X POST "http://localhost:5000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "evening classes",
    "n_results": 5,
    "filter": {"location": {"$eq": "London"}}
  }'
```

## Supported Filter Operators

V2 Collections support the following operators:

- `$eq`: Equals
- `$ne`: Not equals
- `$lt`: Less than
- `$lte`: Less than or equal
- `$gt`: Greater than
- `$gte`: Greater than or equal
- `$and`: Logical AND
- `$or`: Logical OR
- `$not`: Logical NOT

## Important Notes

1. **Filterable Fields**: Only fields defined in `data_schema.properties` can be used for filtering in V2
2. **Vector Field Name**: Must be named "embedding" to match the default (or configure `vector_field_name`)
3. **Dimensions**: Must match your embedding model (768 for text-embedding-005)
4. **Backward Compatibility**: The provider still supports V1 for existing deployments

## Rollback Plan

If you need to rollback to V1:

1. Update `.env`:
   ```bash
   VERTEX_AI_API_VERSION=v1
   VERTEX_AI_INDEX_ID=your-old-index-id
   VERTEX_AI_INDEX_ENDPOINT_ID=your-old-endpoint-id
   ```

2. Restart your application

The provider will automatically use V1 API.

## Benefits of V2

- **Simpler Setup**: One collection instead of Index + Endpoint + storage
- **Unified Data Model**: Vectors, metadata, and content in one place
- **Better Performance**: Optimized for common use cases
- **Easier Filtering**: Dict-based syntax is more intuitive
- **Lower Latency**: Reduced overhead from unified storage

## Resources

- [Vertex AI Vector Search 2.0 Documentation](https://cloud.google.com/vertex-ai/docs/vector-search-2)
- [Collections Guide](https://cloud.google.com/vertex-ai/docs/vector-search-2/collections)
- [Query Syntax](https://cloud.google.com/vertex-ai/docs/vector-search-2/query-search)
- [Migration Guide](https://cloud.google.com/vertex-ai/docs/vector-search-2/migrate)

## Support

If you encounter issues during migration:

1. Check the logs for detailed error messages
2. Verify your GCP permissions (Vertex AI User role)
3. Ensure the collection was created successfully
4. Confirm environment variables are set correctly
5. Test with a small dataset first before full reindex
