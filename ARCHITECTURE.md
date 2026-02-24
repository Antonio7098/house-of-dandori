# Architecture Documentation

## Overview

The School of Dandori course management platform is built with a layered architecture that separates concerns and enables flexibility in deployment.

---

## Tech Stack

- **Backend**: Flask (Python 3.12)
- **Database**: PostgreSQL (hosted on Supabase)
- **Vector Store**: 
  - ChromaDB (local development)
  - Vertex AI Vector Search 2.0 with Collections (production)
- **Embeddings**: Vertex AI text-embedding-005
- **Deployment**: Google Cloud Run
- **PDF Processing**: PyPDF2

---

## File Structure

```
.
├── app.py                    # Application entry point
├── Dockerfile                # Container configuration
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── AGENTS.md                # Developer/AI agent guide
├── ARCHITECTURE.md          # This file
│
├── src/
│   ├── api/
│   │   ├── app.py          # Flask app factory
│   │   ├── routes.py       # Course CRUD endpoints
│   │   ├── search.py       # Vector search endpoints
│   │   └── auth.py        # Authentication endpoints
│   │
│   ├── core/
│   │   ├── config.py       # Configuration & environment
│   │   ├── errors.py       # Error taxonomy & custom exceptions
│   │   ├── logging.py      # Structured logging
│   │   ├── auth.py         # JWT authentication service
│   │   ├── utils.py        # Utility functions
│   │   └── vector_store/
│   │       ├── base.py     # Vector store interface
│   │       ├── chroma.py   # ChromaDB implementation
│   │       └── vertexai.py # Vertex AI implementation
│   │
│   ├── models/
│   │   ├── database.py     # Database operations
│   │   ├── schemas.py      # Pydantic validation schemas
│   │   └── __init__.py     # Course extraction from PDFs
│   │
│   └── services/
│       ├── rag_service.py  # Vector search abstraction
│       └── graph_rag_service.py # GraphRAG dual-collection hybrid search
│
├── templates/
│   ├── index.html          # Main UI
│   ├── login.html         # Login page
│   └── signup.html        # Signup page
│
└── tests/
    ├── conftest.py         # Test fixtures
    └── test_api.py         # API tests
```

---

## Backend Architecture

### Layered Structure

1. **API Layer** (`src/api/`)
   - Flask blueprints define routes
   - Handle HTTP requests/responses
   - Input validation

2. **Service Layer** (`src/services/`)
   - Business logic abstraction
   - RAG service handles vector operations

3. **Core Layer** (`src/core/`)
   - Configuration management
   - Error taxonomy & custom exceptions
   - Structured logging
   - Vector store providers (abstract interface + implementations)
   - Utility functions

4. **Model Layer** (`src/models/`)
   - Database operations
   - Pydantic validation schemas
   - Data extraction/transformation

### Key Patterns

- **Blueprint-based routing**: API routes organized in Flask blueprints
- **Provider pattern**: Vector stores implement a common interface
- **Factory pattern**: `VectorStoreFactory.create()` instantiates providers
- **Lazy loading**: Heavy imports inside functions to reduce memory usage
- **Environment-based config**: Runtime behavior controlled via env vars

---

## Error Handling & Validation

### Error Taxonomy (`src/core/errors.py`)

Custom exception hierarchy for consistent error handling:

- `AppError` - Base exception with error codes, categories, and severity
- `ValidationError` - Input validation failures (400)
- `NotFoundError` - Resource not found (404)
- `DatabaseError` - Database operations (500)
- `FileProcessingError` - PDF/upload failures (422)
- `BadRequestError` - Client errors (400)

All errors return structured JSON with `error`, `code`, `category`, and `details`.

### Structured Logging (`src/core/logging.py`)

JSON-formatted logging with:
- Request/response tracking via `api_logger.log_request()`
- Error logging via `api_logger.log_error()`
- Context fields (request_id, user_id, http method/path)

### Pydantic Schemas (`src/models/schemas.py`)

Request/response validation:
- `CourseCreate`, `CourseUpdate` - Input validation
- `CourseResponse` - Response serialization
- `SearchQuery`, `BulkCourseRequest` - Query parameter validation

---

## Database

- **Production**: PostgreSQL (Supabase)
- **Development**: SQLite (local file-based)
- **Connection**: `get_db_connection()` handles both based on `DATABASE_URL` env var

### Schema

```sql
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    class_id VARCHAR(50) UNIQUE,
    title VARCHAR(255),
    instructor VARCHAR(255),
    location VARCHAR(255),
    course_type VARCHAR(100),
    cost VARCHAR(50),
    learning_objectives TEXT,
    provided_materials TEXT,
    skills TEXT,
    description TEXT,
    filename VARCHAR(255),
    pdf_url TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Vector Search

### Providers

- **ChromaDB**: Local development (in-memory or file-based)
- **Vertex AI Vector Search 2.0**: Production deployment using Collections API
  - V2 API uses Collections to store Data Objects with vectors, metadata, and content together
  - Simpler unified data model compared to V1 (Index/Endpoint)
  - Supports advanced filtering with dict-based query syntax

### Embeddings

- **Provider**: Vertex AI
- **Model**: text-embedding-005 (768 dimensions)
- **Usage**: Semantic search for course matching

### API Versions

The Vertex AI provider supports both V1 (legacy) and V2 (recommended) APIs:

- **V2 (Collections)**: Set `VERTEX_AI_API_VERSION=v2` and provide `VERTEX_AI_COLLECTION_ID`
  - Unified data model with vectors, metadata, and content in one place
  - Dict-based filtering: `{"location": {"$eq": "London"}}`
  - Simpler setup and management
  
- **V1 (Index/Endpoint)**: Legacy support for existing deployments
  - Requires `VERTEX_AI_INDEX_ID` and `VERTEX_AI_INDEX_ENDPOINT_ID`
  - Separate document storage required

### Lazy Loading

Vector store providers are lazy-loaded to reduce memory usage. In development mode, ChromaDB is used with in-memory storage and reindexes on startup. In production, Vertex AI Vector Search 2.0 is used with persistent Collections (no startup reindex needed).

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/courses` | List courses with filters |
| GET | `/api/courses/<id>` | Get single course |
| POST | `/api/courses` | Create course |
| PUT | `/api/courses/<id>` | Update course |
| DELETE | `/api/courses/<id>` | Delete course |
| POST | `/api/upload` | Upload PDF |
| GET | `/api/search` | Semantic search |
| GET | `/api/graph-search` | GraphRAG hybrid search |
| POST | `/api/index` | Index courses |
| POST | `/api/graph-index` | Index GraphRAG collections |
| POST | `/api/reindex` | Reindex courses |
| GET | `/api/config` | Get config |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | SQLite (local) |
| `DB_PATH` | SQLite database path | `courses.db` |
| `OPENROUTER_API_KEY` | API key for embeddings (ChromaDB only) | Required for ChromaDB |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `VECTOR_STORE_PROVIDER` | `chroma` or `vertexai` | auto-set by ENVIRONMENT |
| `CHROMA_PERSIST_DIR` | Directory to persist ChromaDB files | None |
| `GCP_PROJECT_ID` | Google Cloud project ID | Required for Vertex AI |
| `GCP_LOCATION` | GCP region (e.g., europe-west2) | `us-central1` |
| `VERTEX_AI_API_VERSION` | `v2` (Collections) or `v1` (Index/Endpoint) | `v1` |
| `VERTEX_AI_COLLECTION_ID` | Collection ID for V2 API | Required for V2 |
| `VERTEX_AI_INDEX_ID` | Index ID for V1 API (legacy) | Required for V1 |
| `VERTEX_AI_INDEX_ENDPOINT_ID` | Endpoint ID for V1 API (legacy) | Required for V1 |
| `GRAPH_RAG_KG_COLLECTION` | Chroma collection name for KG triples | `graph_kg_triples` |
| `GRAPH_RAG_CHUNK_COLLECTION` | Chroma collection name for course chunks | `graph_course_chunks` |
| `GRAPH_RAG_LLM_MODEL` | LLM model for GraphRAG answers | `openai/gpt-4o-mini` |
| `SUPABASE_URL` | Supabase project URL | - |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key | - |
| `SUPABASE_SECRET_KEY` | Supabase secret key | - |
| `DEV_BYPASS_AUTH` | Skip auth in development | `true` in development |
