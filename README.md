# School of Dandori - Course Management API

A Flask-based REST API for managing wellness courses, with semantic search powered by vector embeddings.

## Overview

The School of Dandori teaches wellbeing through whimsical evening and weekend classes. This platform allows customers to browse, search, and register for courses while instructors can submit and manage their offerings.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture documentation.

## Features

- RESTful API for course CRUD operations
- Semantic search using vector embeddings
- PDF upload and automatic course data extraction
- Filtering by location and course type
- GraphRAG hybrid retrieval (ChromaDB) with optional Neo4j adjacency traversal

## Getting Started

### Prerequisites

- Python 3.12+
- Docker (for local PostgreSQL)
- PostgreSQL (or SQLite for local dev without Docker)

### Installation

```bash
# Clone and setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start local PostgreSQL with Docker (if using Supabase, skip)
docker compose up -d

# Start Neo4j (only needed if GRAPH_RAG_USE_NEO4J=true)
docker start dandori-neo4j

# ChromaDB is created automatically by the app; no separate container needed

# Run locally (reindexing disabled by default)
python app.py
```

### Running Tests

```bash
python3 -m pytest tests/ -v
```

**Always run tests before pushing to remote.**

## Ingesting Courses

Courses can be ingested from PDFs in two ways:

### Option 1: Using the UI

1. Open the web interface
2. Select one or more PDF files using the file picker
3. Click "Upload & Process"
4. The courses will be extracted and added to the database

### Option 2: Using the CLI Script

```bash
# Using local server (default)
python scripts/ingest_pdfs.py /path/to/pdfs

# Using custom API URL
python scripts/ingest_pdfs.py /path/to/pdfs --api-url https://your-api-url
```

## Quick Reference

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/courses` | List courses with optional filters |
| GET | `/api/courses/<id>` | Get single course |
| POST | `/api/courses` | Create course |
| PUT | `/api/courses/<id>` | Update course |
| DELETE | `/api/courses/<id>` | Delete course |
| POST | `/api/upload` | Upload single PDF to extract course |
| POST | `/api/upload/batch` | Upload multiple PDFs |
| GET | `/api/search` | Semantic vector search |
| GET | `/api/graph-search` | GraphRAG hybrid search (returns KG + chunks only) |
| GET | `/api/graph-neighbors` | Fetch adjacent nodes from Neo4j GraphRAG store |
| POST | `/api/index` | Index courses to vector store |
| POST | `/api/graph-index` | Index courses for GraphRAG |
| POST | `/api/reindex` | Reindex all courses |
| GET | `/api/config` | Get vector indexing status |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | `development` or `production` | `development` |
| `DATABASE_URL` | PostgreSQL connection string | SQLite (local) |
| `OPENROUTER_API_KEY` | API key for embeddings | Required |
| `VECTOR_STORE_PROVIDER` | `chroma` or `vertexai` | auto-set by ENVIRONMENT |
| `CHROMA_PERSIST_DIR` | Directory to persist ChromaDB files | auto-created if omitted |
| `GRAPH_RAG_USE_NEO4J` | Toggle Neo4j graph persistence (`true`/`false`) | `false` |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j connection config (only needed when enabled) | `bolt://localhost:7687`, `neo4j`, *(required)* |
| `REINDEX_ON_STARTUP` | Set to `false` to skip auto-indexing on boot | `true` |
| `REINDEX_MAX_COURSES` | Limit number of courses indexed at startup (blank = all) | *(unset)* |

> The rest of the GraphRAG tuning knobs (collection names, batch size, chunk cap, etc.) now ship with sensible in-code defaults, so no extra environment entries are needed unless you want to override them.

### GraphRAG Enrichment Overview

GraphRAG indexing mirrors `graph_rag_analysis.ipynb`:

1. **Base triples**: `has_instructor`, `is_of_type`, `taught_at`.
2. **Narrative chunks**: consolidated course metadata (skills, objectives, materials, descriptions).
3. **Advanced NLP**:
   - Token frequency + coverage filtering (noise tokens like `skill` removed).
   - Flexible n-gram mining across sliding windows.
   - Phrase candidates (`Creative Cooking`, `Wildlife Conservation`, etc.).
   - KMeans clustering (scikit-learn) to map tokens/phrases into five themes.
4. **Enriched predicates**: Courses get `teaches_concept`, `develops_proficiency_in`, `provides_material`, and `belongs_to_theme`. Clustered phrases also receive `belongs_to_theme` edges. The resulting triples are written to both ChromaDB (for retrieval) and, when `GRAPH_RAG_USE_NEO4J=true`, into Neo4j via `/api/graph-index`.

`/api/graph-search` now returns only retrieval payloads; downstream chat endpoints handle any LLM generation. Use `/api/graph-neighbors?value=<node>&limit=25` to inspect adjacent entities from Neo4j.

### Neo4j & Disk Usage Tips

- Start the local database with `docker start dandori-neo4j` before hitting `/api/graph-index` when `GRAPH_RAG_USE_NEO4J=true`.
- Use the `limit` query parameter (e.g., `/api/graph-index?limit=200`) to reindex only a subset of courses while iterating.
- The `GRAPH_RAG_MAX_CHUNK_CHARS` guard truncates very verbose descriptions to keep `chroma_data/` under control; tweak as needed.
