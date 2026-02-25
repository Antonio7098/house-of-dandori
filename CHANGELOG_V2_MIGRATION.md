# Vertex AI Vector Search V2 Migration - Changelog

## Summary

Migrated the School of Dandori project from Vertex AI Vector Search V1 (Index/Endpoint) to V2 (Collections) API. This provides a simpler, more unified data model with better performance and easier filtering.

## Changes Made

### 1. Core Implementation (`src/core/vector_store/vertexai.py`)

**Updated `VertexAIVectorSearchProvider` class:**
- Added support for both V1 (legacy) and V2 (Collections) APIs
- New parameters:
  - `collection_id`: For V2 Collections
  - `api_version`: "v1" or "v2" to select API version
- Automatic API version detection from environment variables
- Separate implementation methods:
  - `_add_v2()` / `_add_v1()` for adding documents
  - `_delete_v2()` / `_delete_v1()` for deleting documents
  - `_query_v2()` / `_query_v1()` for searching
- V2 filtering support with dict-based query syntax
- Lazy-loading of V2 client (`vectorsearch_v1beta`)

**Key Features:**
- Backward compatible with V1 deployments
- Unified data model in V2 (vectors + metadata + content)
- Dict-based filtering: `{"location": {"$eq": "London"}}`
- Proper document content storage in `page_content` field

### 2. Environment Configuration

**Updated `.env.example`:**
```bash
# V2 (recommended)
VERTEX_AI_API_VERSION=v2
VERTEX_AI_COLLECTION_ID=your-collection-id

# V1 (legacy, commented out)
# VERTEX_AI_INDEX_ID=your-index-id
# VERTEX_AI_INDEX_ENDPOINT_ID=your-index-endpoint-id
```

**Updated `.env`:**
- Set `VERTEX_AI_API_VERSION=v2`
- Set `VERTEX_AI_COLLECTION_ID=dandori-courses-collection`
- Commented out old V1 settings for reference

### 3. Dependencies (`requirements.txt`)

**Updated:**
- `google-cloud-aiplatform>=1.70.0` (was >=1.38.0)
  - Required for Vector Search 2.0 support
- Removed `gcloud` (not needed)

### 4. Migration Scripts

**Created `scripts/create_vertex_collection.py`:**
- Automated collection creation script
- Checks if collection already exists
- Creates collection with proper schema:
  - Filterable fields: `id`, `course_type`, `location`, `instructor`, `cost`, `page_content`
  - Vector field: `embedding` (768 dimensions)
- Waits for operation completion
- Provides clear success/error messages

**Created `scripts/README.md`:**
- Documentation for the collection creation script
- Usage instructions
- Troubleshooting guide

### 5. Documentation

**Updated `ARCHITECTURE.md`:**
- Updated Tech Stack section to mention V2
- Added Vector Search API Versions section
- Updated Environment Variables table with V2 settings
- Clarified embedding provider (Vertex AI text-embedding-005)

**Created `docs/VERTEX_AI_V2_MIGRATION.md`:**
- Complete migration guide
- Key differences between V1 and V2
- Step-by-step migration instructions
- Filtering syntax comparison
- Supported operators reference
- Rollback plan
- Benefits of V2
- Troubleshooting tips

**Created `CHANGELOG_V2_MIGRATION.md`:**
- This file - comprehensive change summary

## Migration Path

### For New Deployments

1. Set environment variables:
   ```bash
   VERTEX_AI_API_VERSION=v2
   VERTEX_AI_COLLECTION_ID=dandori-courses-collection
   ```

2. Create collection:
   ```bash
   python scripts/create_vertex_collection.py
   ```

3. Deploy and index:
   ```bash
   curl -X POST http://localhost:5000/api/index
   ```

### For Existing V1 Deployments

1. Create V2 collection (see above)
2. Update environment variables
3. Restart application
4. Reindex data
5. Test thoroughly
6. Keep V1 settings commented out for rollback

## Backward Compatibility

The implementation maintains full backward compatibility:
- V1 deployments continue to work without changes
- Set `VERTEX_AI_API_VERSION=v1` to use legacy API
- Provider automatically selects correct implementation

## Benefits of V2

1. **Simpler Setup**: One collection vs Index + Endpoint + storage
2. **Unified Data Model**: Everything in one place
3. **Better Performance**: Optimized architecture
4. **Easier Filtering**: Intuitive dict-based syntax
5. **Lower Latency**: Reduced overhead

## Testing Checklist

- [ ] Collection created successfully
- [ ] Environment variables updated
- [ ] Application starts without errors
- [ ] Basic search works
- [ ] Filtered search works
- [ ] Document addition works
- [ ] Document deletion works
- [ ] Performance is acceptable

## Rollback Procedure

If issues occur:

1. Update `.env`:
   ```bash
   VERTEX_AI_API_VERSION=v1
   VERTEX_AI_INDEX_ID=your-old-index-id
   VERTEX_AI_INDEX_ENDPOINT_ID=your-old-endpoint-id
   ```

2. Restart application

3. Verify V1 functionality

## Next Steps

1. **Create the collection** using the provided script
2. **Test locally** with development data
3. **Update production** environment variables
4. **Deploy** to Cloud Run
5. **Monitor** performance and errors
6. **Optimize** based on usage patterns

## Resources

- [Vertex AI Vector Search 2.0 Docs](https://cloud.google.com/vertex-ai/docs/vector-search-2)
- [Collections Guide](https://cloud.google.com/vertex-ai/docs/vector-search-2/collections)
- [Query Syntax](https://cloud.google.com/vertex-ai/docs/vector-search-2/query-search)
- [Official Migration Guide](https://cloud.google.com/vertex-ai/docs/vector-search-2/migrate)

## Questions for Understanding

To test your understanding of this migration:

1. **Why did we migrate to V2?** What are the key benefits over V1?

2. **How does the provider maintain backward compatibility?** What happens if someone sets `api_version="v1"`?

3. **What's the difference in filtering syntax?** Can you write a V2 filter for "courses in London under £50"?

4. **Why must filterable fields be defined in the schema?** What happens if you try to filter on an undefined field?

5. **What would happen if you forgot to set `VERTEX_AI_API_VERSION`?** How does the code handle this?

## Commit Message

```
feat: migrate to Vertex AI Vector Search 2.0 Collections API

- Update VertexAIVectorSearchProvider to support both V1 and V2 APIs
- Add V2 Collections support with dict-based filtering
- Create collection setup script with automated schema configuration
- Update documentation with migration guide and API comparison
- Maintain backward compatibility with V1 deployments
- Upgrade google-cloud-aiplatform to >=1.70.0

BREAKING CHANGE: New deployments should use V2 Collections.
Existing V1 deployments continue to work but should migrate.

See docs/VERTEX_AI_V2_MIGRATION.md for migration instructions.
```
