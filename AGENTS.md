# AGENTS.md - Developer & AI Agent Guide

## Project Context

### What is Dandori?
Dandori is the art of managing one's resources efficiently to maximise output. At the School of Dandori, the resource being managed is time and wellbeing. The philosophy is that we should enjoy our time and look after our holistic self.

### Who are the School of Dandori?
The School of Dandori teaches wellbeing and encourages people to reconnect with their younger, more carefree days. Exclusively for adults, they offer evening and weekend classes in delightful topics with an air of whimsy.

Founded in 2017 by Ada Calm and Tessa Forman—two technologists who believed humans need to reclaim attention from machines. The team is small: Ada handles finances, Tessa handles marketing, and Arthur Ingham built and manages the technology platform.

The School works with hundreds of freelance instructors across the UK. This platform allows customers to register and pay for courses, and sends instructors their participant list and share of fees.

### The Project
Facing challenges with scaling, they've embraced AI to help onboard new instructors and increase capacity while maintaining their playful, human-centered approach.

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

## Development Guidelines

### Before Pushing

1. **Run tests:**
   ```bash
   python3 -m pytest tests/ -v
   ```

2. **Update documentation** if you've made changes that affect:
   - API endpoints (update README.md)
   - Architecture or patterns (update AGENTS.md)
   - Environment variables (update both README.md and AGENTS.md)

3. **Use conventional commits:**
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Adding/updating tests
   - `chore:` - Maintenance tasks
   
   Example: `feat: add vector search endpoint for semantic course matching`

### Project Organization

When adding new features or files:
- Follow the existing architectural patterns in the codebase
- Place new routes in appropriate blueprint files
- Keep the file structure consistent (see below)
- Consider lazy loading for heavy dependencies

---

## File Structure

```
.
├── app.py                    # Application entry point
├── Dockerfile                # Container configuration
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── AGENTS.md                # Developer/AI agent guide
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

### Database

- PostgreSQL (Supabase) for production
- SQLite for local development
- `get_db_connection()` handles both based on `DATABASE_URL` env var

### Vector Search

- ChromaDB for local development (in-memory or file-based)
- Vertex AI Vector Search for production
- OpenRouter API for embeddings (google/gemini-embedding-001)

---

## Testing

Tests use an in-memory SQLite database via `tests/conftest.py`. The fixture sets `DB_PATH` before each test to ensure isolation.

---

## Mentoring & Learning

After implementing a feature, prompt the user with questions to test their understanding:

1. **Explain what you did** - Walk through how the new component works
2. **Test their understanding** - Ask probing questions like:
   - "Why do you think we used X instead of Y?"
   - "What would happen if we changed Z?"
   - "Can you explain how the data flows through this?"
3. **Suggest extensions** - Encourage trying variations or additions
4. **Discuss tradeoffs** - Analyze pros/cons of different approaches
5. **Foster critical thinking** - Challenge assumptions and explore alternatives

This helps build deep understanding of the codebase and software engineering principles.
