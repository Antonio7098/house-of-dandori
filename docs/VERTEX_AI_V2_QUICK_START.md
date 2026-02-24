# Vertex AI Vector Search 2.0 - Quick Start

## TL;DR

```bash
# 1. Update .env
VERTEX_AI_API_VERSION=v2
VERTEX_AI_COLLECTION_ID=dandori-courses-collection

# 2. Create collection
python scripts/create_vertex_collection.py

# 3. Restart app and reindex
curl -X POST http://localhost:5000/api/index

# Done! 🎉
```

## What Changed?

**Before (V1):**
- Index + Endpoint + separate storage
- Complex setup
- Namespace-based filtering

**After (V2):**
- Single Collection
- Simple setup
- Dict-based filtering

## Filtering Examples

### V1 (Old)
```python
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace

filters = [Namespace(name="location", allow_tokens=["London"])]
```

### V2 (New)
```python
# Simple
filter = {"location": {"$eq": "London"}}

# Complex
filter = {
    "$and": [
        {"location": {"$eq": "London"}},
        {"cost": {"$lt": "50"}}
    ]
}
```

## Operators

- `$eq` - Equals
- `$ne` - Not equals
- `$lt` - Less than
- `$lte` - Less than or equal
- `$gt` - Greater than
- `$gte` - Greater than or equal
- `$and` - Logical AND
- `$or` - Logical OR
- `$not` - Logical NOT

## Environment Variables

```bash
# Required
GCP_PROJECT_ID=my-project-oscar-487814
GCP_LOCATION=europe-west2

# V2 (recommended)
VERTEX_AI_API_VERSION=v2
VERTEX_AI_COLLECTION_ID=dandori-courses-collection

# V1 (legacy - for rollback only)
# VERTEX_AI_API_VERSION=v1
# VERTEX_AI_INDEX_ID=your-index-id
# VERTEX_AI_INDEX_ENDPOINT_ID=your-endpoint-id
```

## Troubleshooting

**"Collection not found"**
→ Run `python scripts/create_vertex_collection.py`

**"Permission denied"**
→ Run `gcloud auth application-default login`

**"No module named google.cloud.vectorsearch_v1beta"**
→ Run `pip install -r requirements.txt`

**Search returns no results**
→ Reindex: `curl -X POST http://localhost:5000/api/index`

## Need More Details?

See [VERTEX_AI_V2_MIGRATION.md](VERTEX_AI_V2_MIGRATION.md) for the complete guide.
