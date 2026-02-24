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

# Start local PostgreSQL with Docker
docker compose up -d

# Configure environment
cp .env.docker .env.local
source .env.local

# Run locally
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
| POST | `/api/index` | Index courses to vector store |
| POST | `/api/reindex` | Reindex all courses |
| GET | `/api/config` | Get vector indexing status |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | `development` or `production` | `development` |
| `DATABASE_URL` | PostgreSQL connection string | SQLite (local) |
| `OPENROUTER_API_KEY` | API key for embeddings | Required |
| `VECTOR_STORE_PROVIDER` | `chroma` or `vertexai` | auto-set by ENVIRONMENT |
