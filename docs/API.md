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

---

## API Endpoints

### Health Check

#### GET /api/health

Check if the API is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Courses

#### GET /api/courses

List courses with optional filters and pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| search | string | No | "" | Search in title, class_id, description |
| location | string | No | "" | Filter by location |
| course_type | string | No | "" | Filter by course type |
| page | integer | No | 1 | Page number (1-indexed) |
| limit | integer | No | 20 | Items per page (max 100) |

**Response:**
```json
{
  "count": 150,
  "page": 1,
  "limit": 20,
  "total_pages": 8,
  "courses": [
    {
      "id": 1,
      "class_id": "CLASS_123",
      "title": "Pottery for Beginners",
      "instructor": "Jane Smith",
      "location": "London",
      "course_type": "Workshop",
      "cost": "£45",
      "learning_objectives": ["Learn wheel throwing", "Hand-building techniques"],
      "provided_materials": ["Clay", "Glazes", "Tools"],
      "skills": ["Creativity", "Patience"],
      "description": "A fun introductory pottery class...",
      "filename": "class_123.pdf",
      "pdf_url": null,
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T10:00:00"
    }
  ]
}
```

---

#### GET /api/courses/{id}

Get a single course by ID.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Course ID |

**Response (200):**
```json
{
  "id": 1,
  "class_id": "CLASS_123",
  "title": "Pottery for Beginners",
  "instructor": "Jane Smith",
  "location": "London",
  "course_type": "Workshop",
  "cost": "£45",
  "learning_objectives": ["Learn wheel throwing"],
  "provided_materials": ["Clay", "Tools"],
  "skills": ["Creativity"],
  "description": "A fun introductory pottery class...",
  "filename": "class_123.pdf",
  "pdf_url": null,
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00"
}
```

**Response (404):**
```json
{
  "error": "Course not found",
  "code": "NOT_FOUND",
  "category": "not_found",
  "severity": "info",
  "details": {
    "resource": "Course",
    "identifier": "999"
  }
}
```

---

#### POST /api/courses

Create a new course.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | Yes | Course title (1-255 chars) |
| class_id | string | No | Unique class identifier |
| instructor | string | No | Instructor name |
| location | string | No | Course location |
| course_type | string | No | Type of course (e.g., "Workshop") |
| cost | string | No | Course cost |
| learning_objectives | array | No | List of learning objectives |
| provided_materials | array | No | List of materials provided |
| skills | array | No | List of skills taught |
| description | string | No | Course description |

**Request Example:**
```json
{
  "title": "Watercolor Painting",
  "class_id": "CLASS_456",
  "instructor": "John Doe",
  "location": "Oxford",
  "course_type": "Workshop",
  "cost": "£35",
  "learning_objectives": ["Basic brush techniques", "Color mixing"],
  "provided_materials": ["Paints", "Brushes", "Paper"],
  "skills": ["Creativity", "Focus"],
  "description": "Learn the basics of watercolor painting"
}
```

**Response (201):**
```json
{
  "id": 2,
  "message": "Course created"
}
```

**Response (400):**
```json
{
  "error": "Input should be a valid string",
  "code": "VALIDATION_ERROR",
  "category": "validation",
  "severity": "warning",
  "details": {...}
}
```

---

#### PUT /api/courses/{id}

Update an existing course.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Course ID |

**Request Body:**

All fields from POST /api/courses are optional. Only include fields you want to update.

**Response (200):**
```json
{
  "message": "Course updated"
}
```

---

#### DELETE /api/courses/{id}

Delete a course.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Course ID |

**Response (200):**
```json
{
  "message": "Course deleted"
}
```

---

#### POST /api/courses/bulk

Get multiple courses by IDs.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ids | array | Yes | Array of course IDs (1-100) |

**Request Example:**
```json
{
  "ids": [1, 2, 3, 4, 5]
}
```

**Response (200):**
```json
{
  "courses": [
    {...},
    {...}
  ]
}
```

---

### File Upload

#### POST /api/upload

Upload a PDF file to extract course data automatically.

**Content-Type:** `multipart/form-data`

**Form Data:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | Yes | PDF file to upload |

**Response (201):**
```json
{
  "id": 3,
  "message": "Course created",
  "data": {
    "class_id": "CLASS_789",
    "title": "Yoga for Stress Relief",
    "instructor": "Alice Johnson",
    "location": "Harrogate",
    "course_type": "Wellness",
    "cost": "£25",
    "learning_objectives": [...],
    "provided_materials": [...],
    "skills": [...],
    "description": "...",
    "filename": "abc123_class_789.pdf"
  }
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | No file provided |
| 400 | No file selected |
| 400 | Only PDF files are allowed |
| 422 | Failed to extract data from PDF |

---

#### POST /api/upload/batch

Upload multiple PDF files at once.

**Content-Type:** `multipart/form-data`

**Form Data:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| files | file[] | Yes | Array of PDF files (max 50) |

**Response (200):**
```json
{
  "total": 10,
  "successful": 8,
  "failed": 2,
  "results": [
    {
      "filename": "class_123.pdf",
      "success": true,
      "course_id": 1,
      "title": "Pottery for Beginners"
    },
    {
      "filename": "invalid.pdf",
      "success": false,
      "error": "Failed to extract data from PDF"
    }
  ]
}
```

---

### Chat

#### POST /api/chat

Tool-calling chat endpoint with optional SSE streaming. The model can call `search_courses`, `semantic_search`, and (in graphrag mode) `graph_neighbors`. Before any tool is called, the backend enriches the prompt with initial context (SQL quick search, semantic snippets, and graph neighbors). Tool results are summarized and injected back into the conversation before the final answer, ensuring follow-up questions are grounded in the latest tool output.

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| message | string | Yes | - | User message |
| history | array | No | [] | Last 10 user/assistant/system turns |
| mode | string | No | "standard" | "standard" or "graphrag" |
| filters | object | No | {} | SQL filters for search_courses |
| stream | boolean | No | false | Enable SSE streaming |
| model | string | No | env `CHAT_MODEL` | OpenAI/OpenRouter model ID |

**Request Example:**
```json
{
  "message": "What are the skills for The Art of Lush Leaf Lamentation?",
  "history": [
    {"role": "user", "content": "I like nature"},
    {"role": "assistant", "content": "Here are some nature-themed courses..."}
  ],
  "mode": "standard",
  "stream": true
}
```

**Non-streaming Response (200):**
```json
{
  "message": "The Art of Lush Leaf Lamentation teaches: Botany, Crafting, Emotional Awareness, Artistry, Nature Exploration.",
  "artifacts": [],
  "mode": "standard",
  "model": "openai/gpt-4o-mini",
  "tool_events": [
    {
      "event": "tool_call",
      "id": "call_abc",
      "name": "search_courses",
      "arguments": {"query": "Lush Leaf Lamentation"},
      "status": "running"
    },
    {
      "event": "tool_result",
      "id": "call_abc",
      "name": "search_courses",
      "arguments": {"query": "Lush Leaf Lamentation"},
      "status": "completed",
      "result": {"courses": [...]}
    }
  ]
}
```

**Streaming Response (SSE):**
Events are emitted in order:
- `tool_call` – when a tool starts
- `tool_result` – when a tool finishes
- `text_delta` – incremental markdown tokens
- `message_end` – final message + artifacts

**SSE Event Types:**
| Event | Payload | Meaning |
|-------|---------|---------|
| tool_call | `{id, name, arguments, status: "running"}` | Tool execution started |
| tool_result | `{id, name, arguments, status: "completed"|"error", result}` | Tool finished |
| text_delta | `{delta}` | Incremental assistant markdown |
| message_end | `{message, artifacts, mode, model}` | End of stream |

**History Guidance:** Include at most the last 10 user/assistant/system messages to keep prompts lean while preserving context.

---

### Search

#### GET /api/search

Semantic vector search for courses.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| q | string | Yes | - | Search query |
| page | integer | No | 1 | Page number |
| n | integer | No | 10 | Number of results (max 100) |

**Response (200):**
```json
{
  "results": [
    {
      "id": 5,
      "class_id": "CLASS_111",
      "title": "Mindful Pottery",
      "instructor": "Jane Smith",
      "location": "London",
      "course_type": "Wellness",
      "cost": "£55",
      "learning_objectives": [...],
      "provided_materials": [...],
      "skills": [...],
      "description": "Combine pottery with mindfulness...",
      "filename": "class_111.pdf",
      "pdf_url": null,
      "created_at": "2024-01-20T10:00:00",
      "updated_at": "2024-01-20T10:00:00",
      "_distance": 0.15
    }
  ],
  "count": 15,
  "page": 1,
  "limit": 10,
  "total_pages": 2
}
```

The `_distance` field indicates similarity (lower = more similar).

---

### Vector Indexing

#### POST /api/index

Index all courses to the vector store.

**Response (200):**
```json
{
  "message": "Courses indexed",
  "count": 150
}
```

---

#### POST /api/reindex

Clear and rebuild the entire vector index.

**Response (200):**
```json
{
  "message": "Vector store wiped and re-indexed",
  "count": 150
}
```

---

### Configuration

#### GET /api/config

Get current configuration.

**Response (200):**
```json
{
  "environment": "development",
  "vectorStoreProvider": "chroma",
  "authEnabled": false,
  "supabaseConfigured": false
}
```

---

## Authentication

The API uses Supabase JWT authentication. In development mode, authentication is bypassed.

### Pages

| Route | Description |
|-------|-------------|
| `/login` | Login page |
| `/signup` | Create account page |

### Endpoints

#### POST /api/auth/login

Authenticate user and get JWT token.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User email |
| password | string | Yes | User password |

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com"
  }
}
```

**Dev mode response:**
```json
{
  "token": "dev_token",
  "user": {"email": "dev@localhost", "id": "dev_user"}
}
```

---

#### POST /api/auth/signup

Create a new user account.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User email |
| password | string | Yes | Password (min 6 chars) |

**Response (200):**
```json
{
  "message": "Account created successfully. Please check your email to verify.",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com"
  }
}
```

---

#### POST /api/auth/logout

Logout user (client-side token removal).

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

### Using Authenticated Requests

Include the JWT token in the `Authorization` header:

```bash
curl -X POST http://localhost:5000/api/courses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"title": "New Course"}'
```

### Protected Endpoints

The following endpoints require authentication in production:

- `POST /api/courses` - Create course
- `PUT /api/courses/{id}` - Update course
- `DELETE /api/courses/{id}` - Delete course
- `POST /api/courses/bulk` - Bulk get courses
- `POST /api/upload` - Upload PDF
- `POST /api/upload/batch` - Batch upload PDFs
- `POST /api/index` - Index courses
- `POST /api/reindex` - Reindex courses

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "category": "error_category",
  "severity": "error|warning|info",
  "details": {
    "key": "additional context"
  }
}
```

### Error Codes

| Code | HTTP Status | Category | Description |
|------|-------------|----------|-------------|
| VALIDATION_ERROR | 400 | validation | Request validation failed |
| NOT_FOUND | 404 | not_found | Resource not found |
| ALREADY_EXISTS | 409 | duplicate | Resource already exists |
| DATABASE_ERROR | 500 | database | Database operation failed |
| EXTERNAL_SERVICE_ERROR | 502 | external | External service (e.g., vector store) failed |
| FILE_PROCESSING_ERROR | 422 | file | PDF processing failed |
| BAD_REQUEST | 400 | client | Invalid client request |
| INTERNAL_ERROR | 500 | internal | Unexpected internal error |

---

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

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| ENVIRONMENT | `development` or `production` | `development` |
| DATABASE_URL | PostgreSQL connection string | SQLite (local) |
| DB_PATH | SQLite database path | `courses.db` |
| OPENROUTER_API_KEY | API key for embeddings | Required |
| VECTOR_STORE_PROVIDER | `chroma` or `vertexai` | auto-set by ENVIRONMENT |
