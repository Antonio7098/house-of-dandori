# Scripts

Utility scripts for the School of Dandori project.

## create_vertex_collection.py

Creates a Vertex AI Vector Search 2.0 Collection for storing course embeddings.

### Prerequisites

- Google Cloud project with Vertex AI API enabled
- Appropriate IAM permissions (Vertex AI User role)
- Environment variables configured in `.env`

### Usage

```bash
# Make sure you're in the project root
python scripts/create_vertex_collection.py
```

### Environment Variables Required

```bash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=europe-west2
VERTEX_AI_COLLECTION_ID=dandori-courses-collection
```

### What It Does

1. Checks if the collection already exists
2. Creates a new collection with the proper schema for course data
3. Configures filterable fields: `id`, `course_type`, `location`, `instructor`, `cost`
4. Sets up vector field with 768 dimensions for text-embedding-005
5. Waits for the operation to complete

### Output

```
======================================================================
Vertex AI Vector Search 2.0 Collection Setup
======================================================================

Creating Vertex AI Vector Search Collection...
  Project: my-project-oscar-487814
  Location: europe-west2
  Collection ID: dandori-courses-collection

Sending create collection request...
Operation started: projects/.../operations/...
Waiting for operation to complete (this may take a few minutes)...

✅ Collection created successfully!
Resource name: projects/.../locations/.../collections/...

You can now use this collection in your application.
Make sure your .env file has:
  VERTEX_AI_API_VERSION=v2
  VERTEX_AI_COLLECTION_ID=dandori-courses-collection

======================================================================
Setup complete!
======================================================================
```

### Troubleshooting

**Error: GCP_PROJECT_ID environment variable is required**
- Make sure your `.env` file exists and contains `GCP_PROJECT_ID`

**Error: Permission denied**
- Ensure your GCP account has the Vertex AI User role
- Run `gcloud auth application-default login` to authenticate

**Collection already exists**
- The script will detect existing collections and skip creation
- To recreate, delete the existing collection first via GCP Console

### Next Steps

After creating the collection:

1. Update your `.env` file with V2 settings
2. Restart your application
3. Reindex your courses: `curl -X POST http://localhost:5000/api/index`
4. Test search functionality

See [VERTEX_AI_V2_MIGRATION.md](../docs/VERTEX_AI_V2_MIGRATION.md) for complete migration guide.
