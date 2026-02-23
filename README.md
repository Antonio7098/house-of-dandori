# School of Dandori - Course Management API

A Flask-based REST API for managing wellness courses, with semantic search powered by vector embeddings.

## Overview

The School of Dandori teaches wellbeing through whimsical evening and weekend classes. This platform allows customers to browse, search, and register for courses while instructors can submit and manage their offerings.

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL (Supabase) with SQLite for local development
- **Vector Store**: ChromaDB (local) / Vertex AI Vector Search (production)
- **Deployment**: Google Cloud Run
- **PDF Processing**: PyPDF2

## Features

- RESTful API for course CRUD operations
- Semantic search using vector embeddings
- PDF upload and automatic course data extraction
- Filtering by location and course type

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL (or SQLite for local dev)

### Installation

```bash
# Clone and setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@host/db"  # Optional
export OPENROUTER_API_KEY="your-key"  # For vector embeddings

# Run locally
python app.py
```

### Running Tests

```bash
python3 -m pytest tests/ -v
```

**Always run tests before pushing to remote.**

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/courses` | List courses with optional filters |
| GET | `/api/courses/<id>` | Get single course |
| POST | `/api/courses` | Create course |
| PUT | `/api/courses/<id>` | Update course |
| DELETE | `/api/courses/<id>` | Delete course |
| POST | `/api/upload` | Upload PDF to extract course |
| GET | `/api/search` | Semantic vector search |
| POST | `/api/index` | Index courses to vector store |
| POST | `/api/reindex` | Reindex all courses |
| GET | `/api/config` | Get vector indexing status |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | SQLite (local) |
| `OPENROUTER_API_KEY` | API key for embeddings | Required |
| `VECTOR_STORE_PROVIDER` | `chroma` or `vertexai` | `chroma` |
| `ENABLE_VECTOR_INDEXING` | Enable startup indexing | `true` |
