# Architecture Documentation

## Overview

The School of Dandori course management platform is built with a layered architecture that separates concerns and enables flexibility in deployment.

---

## Tech Stack

- **Backend**: Flask (Python 3.12)
- **Database**: PostgreSQL (hosted on Supabase)
- **Vector Store**: 
  - ChromaDB (local development)
  - Vertex AI Vector Search (production)
- **Embeddings**: OpenRouter API (google/gemini-embedding-001)
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
│   │   └── search.py       # Vector search endpoints
│   │
│   ├── core/
│   │   ├── config.py       # Configuration & environment
│   │   ├── utils.py        # Utility functions
│   │   └── vector_store/
│   │       ├── base.py     # Vector store interface
│   │       ├── chroma.py   # ChromaDB implementation
│   │       └── vertexai.py # Vertex AI implementation
│   │
│   ├── models/
│   │   ├── database.py     # Database operations
│   │   └── __init__.py     # Course extraction from PDFs
│   │
│   └── services/
│       └── rag_service.py  # Vector search abstraction
│
├── templates/
│   └── index.html          # Main UI
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
   - Vector store providers (abstract interface + implementations)
   - Utility functions

4. **Model Layer** (`src/models/`)
   - Database operations
   - Data extraction/transformation

### Key Patterns

- **Blueprint-based routing**: API routes organized in Flask blueprints
- **Provider pattern**: Vector stores implement a common interface
- **Factory pattern**: `VectorStoreFactory.create()` instantiates providers
- **Lazy loading**: Heavy imports inside functions to reduce memory usage
- **Environment-based config**: Runtime behavior controlled via env vars

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
- **Vertex AI Vector Search**: Production deployment

### Embeddings

- **Provider**: OpenRouter API
- **Model**: google/gemini-embedding-001
- **Usage**: Semantic search for course matching

### Lazy Loading

Vector store providers are lazy-loaded to reduce memory usage. In development mode, ChromaDB is used with in-memory storage and reindexes on startup. In production, Vertex AI Vector Search is used with persistent storage (no startup reindex needed).

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
| POST | `/api/index` | Index courses |
| POST | `/api/reindex` | Reindex courses |
| GET | `/api/config` | Get config |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | SQLite (local) |
| `DB_PATH` | SQLite database path | `courses.db` |
| `OPENROUTER_API_KEY` | API key for embeddings | Required |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `VECTOR_STORE_PROVIDER` | `chroma` or `vertexai` | auto-set by ENVIRONMENT |
