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
**Always run tests:**
```bash
python3 -m pytest tests/ -v
```

### Key Files
- `app.py` - Entry point, runs reindex_on_startup() on boot
- `src/api/app.py` - Flask app factory
- `src/api/routes.py` - Course CRUD endpoints
- `src/api/search.py` - Vector search endpoints
- `src/services/rag_service.py` - Vector store abstraction
- `src/core/vector_store/chroma.py` - ChromaDB implementation
- `src/core/vector_store/vertexai.py` - Vertex AI implementation
- `src/models/database.py` - Database operations

### Environment Variables
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `OPENROUTER_API_KEY` | Required for vector embeddings |
| `VECTOR_STORE_PROVIDER` | `chroma` or `vertexai` |
| `ENABLE_VECTOR_INDEXING` | Set to `false` to disable startup indexing (saves memory) |

### Lazy Loading
Vector store providers (ChromaDB, Vertex AI) are lazy-loaded to reduce memory usage when vector indexing is disabled. Import them only inside functions, not at module level.

### Testing
Tests use an in-memory SQLite database via `tests/conftest.py`. The fixture sets `DB_PATH=:memory:` before each test.
