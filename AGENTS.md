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

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full tech stack details.

**IMPORTANT:** Always read [ARCHITECTURE.md](./ARCHITECTURE.md) before making any changes to understand the project's architecture and patterns.

---

## Development Guidelines

### Before Pushing

1. **Run tests:**
   ```bash
   python3 -m pytest tests/ -v
   ```

2. **Update documentation** if you've made changes that affect:
   - API endpoints (update README.md)
   - Architecture or patterns (update ARCHITECTURE.md)
   - Environment variables (update README.md and ARCHITECTURE.md)
   - Developer guidelines (update AGENTS.md)

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
- Keep the file structure consistent (see ARCHITECTURE.md)
- Consider lazy loading for heavy dependencies

---

## Key Files

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
| `ENVIRONMENT` | `development` or `production` | `development` |

### Lazy Loading

Vector store providers (ChromaDB, Vertex AI) are lazy-loaded to reduce memory usage when vector indexing is disabled. Import them only inside functions, not at module level.

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
