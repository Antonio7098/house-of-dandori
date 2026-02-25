# Architecture Documentation

## Overview

The School of Dandori course management platform is built with a layered architecture that separates concerns and enables flexibility in deployment.

---

## Tech Stack

- **Backend**: Flask (Python 3.12)
- **Database**: PostgreSQL (hosted on Supabase)
- **Vector Store**:
  - ChromaDB (local development)
  - Qdrant (managed or self-hosted instances)
  - Vertex AI Vector Search (production)
- **Embeddings**: OpenRouter API (google/gemini-embedding-001)
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
│       ├── __init__.py     # Unified get_service() factory
│       ├── rag_service.py  # Vector search abstraction
│       ├── chat_service.py # Tool-calling chat orchestration + streaming events
│       └── graph_rag_service.py # GraphRAG dual-collection hybrid search
│
├── scripts/
│   └── reindex_services.py # Utility to rebuild vector + graph indices on demand
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

## Chat Service (`src/services/chat_service.py`)

The chat endpoint orchestrates a multi-round tool-calling loop with streaming SSE events and automatic context enrichment.

### Flow Overview

1. **Initial context enrichment** – Before any LLM call, the service builds a lightweight “Initial Dandori context”:
   - Quick SQL search (top 3 matches)
   - Semantic search snippets (top 3 chunks)
   - Graph neighbors (if `mode=graphrag` and Neo4j is enabled)
   This is injected as a system message so the model starts with immediate grounding.

2. **Tool-calling loop** – Up to 5 rounds:
   - The model is forced to call at least one of: `search_courses`, `semantic_search`, or `graph_neighbors`.
   - After the first successful tool call, the loop stops forcing tools and allows the model to synthesize the final answer.
   - Each tool execution emits a `tool_call` event, runs the tool, then emits a `tool_result` event.
   - Tool results are also formatted into human-readable summaries and collected in `tool_context_messages`.

3. **Final narrative pass** – If the model provides no further tool calls:
   - All collected tool summaries are injected back into the conversation as system “Tool context” messages.
   - A final streaming generation pass produces the assistant’s answer, streamed as `text_delta` events.
   - The stream ends with `message_end`, including any resolved `artifacts` from `display(course_id)` tokens.

### SSE Event Types

| Event | Payload | Meaning |
|-------|---------|---------|
| `tool_call` | `{id, name, arguments, status: "running"}` | Tool execution started |
| `tool_result` | `{id, name, arguments, status: "completed"|"error", result}` | Tool finished with JSON-safe result |
| `text_delta` | `{delta}` | Incremental markdown token from the assistant |
| `message_end` | `{message, artifacts, mode, model}` | End of stream; final message and any course artifacts |

### History and Prompt Management

- Frontend should send at most the last 10 user/assistant/system turns in the `history` array.
- The backend always injects the initial context and tool summaries, so the model never operates blind.
- If the loop exhausts rounds without a final answer, a graceful fallback emits a short local-search list.

### Tool Formatters

- `_format_course_results` – Renders SQL course rows with skills/objectives/description.
- `_format_semantic_results` – Lists semantic matches with metadata.
- `_format_graph_results` – Shows graph neighbor labels and scores.

These summaries are the “Tool context” injected before the final answer, ensuring follow-up questions (“what are the skills?”, “who teaches course 3?”) are grounded in the latest tool output.

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

### Providers & Index Lifecycle

- **ChromaDB**: Local development (in-memory or file-based)
<<<<<<< HEAD
- **Vertex AI Vector Search**: Production deployment
- **Reindex tooling**: `scripts/reindex_services.py --mode both` invokes the shared `get_service()` factory so that both the simple RAG and GraphRAG services rebuild their collections from the `courses` table without needing authenticated API calls.
=======
- **Vertex AI Vector Search 2.0**: Production deployment using Collections API
  - V2 API uses Collections to store Data Objects with vectors, metadata, and content together
  - Simpler unified data model compared to V1 (Index/Endpoint)
  - Supports advanced filtering with dict-based query syntax
>>>>>>> origin/Front2Back

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
| GET | `/api/graph-search` | GraphRAG hybrid search (Chroma KG + chunks) |
| GET | `/api/graph-neighbors` | Neo4j adjacency traversal for GraphRAG |
| POST | `/api/chat` | Tool-calling chat endpoint (supports SSE stream + tool events) |
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
| `VECTOR_STORE_PROVIDER` | `chroma`, `qdrant`, or `vertexai` | auto-set by ENVIRONMENT |
| `CHROMA_PERSIST_DIR` | Directory to persist ChromaDB files | None |
<<<<<<< HEAD
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant endpoint + API key (required for `qdrant`) | None |
| `QDRANT_COLLECTION` | Override default Qdrant collection name | `courses` |
| `QDRANT_PREFER_GRPC` | Set to `true` to toggle gRPC transport | None |
| `GRAPH_RAG_VECTOR_PROVIDER` | Forces GraphRAG to use a specific provider (`chroma` by default) | `chroma` |
=======
| `GCP_PROJECT_ID` | Google Cloud project ID | Required for Vertex AI |
| `GCP_LOCATION` | GCP region (e.g., europe-west2) | `us-central1` |
| `VERTEX_AI_API_VERSION` | `v2` (Collections) or `v1` (Index/Endpoint) | `v1` |
| `VERTEX_AI_COLLECTION_ID` | Collection ID for V2 API | Required for V2 |
| `VERTEX_AI_INDEX_ID` | Index ID for V1 API (legacy) | Required for V1 |
| `VERTEX_AI_INDEX_ENDPOINT_ID` | Endpoint ID for V1 API (legacy) | Required for V1 |
>>>>>>> origin/Front2Back
| `GRAPH_RAG_KG_COLLECTION` | Chroma collection name for KG triples | `graph_kg_triples` |
| `GRAPH_RAG_CHUNK_COLLECTION` | Chroma collection name for course chunks | `graph_course_chunks` |
| `GRAPH_RAG_BATCH_SIZE` | Batch size when writing Chroma collections | `2000` |
| `GRAPH_RAG_MAX_CHUNK_CHARS` | Caps per-chunk text length to control disk usage | `2000` |
| `GRAPH_RAG_USE_NEO4J` | Enables Neo4j graph persistence | `false` |
| `GRAPH_RAG_NEO4J_BATCH_SIZE` | Relationships per batch when writing to Neo4j | `500` |
| `REINDEX_ON_STARTUP` | Enables automatic reindex during app boot (dev only) | `false` |
| `DEV_BYPASS_AUTH` | Skip auth in development | `true` in development |
| `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` | Neo4j connection information | `bolt://localhost:7687`, `neo4j`, *(required)* |
| `SUPABASE_URL` | Supabase project URL | - |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key | - |
| `SUPABASE_SECRET_KEY` | Supabase secret key | - |
