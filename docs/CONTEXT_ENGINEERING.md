---
description: Deep context engineering reference for School of Dandori services
---

# Context Engineering Playbook

This document stitches together everything that shapes *"context"* inside the Dandori platform—from how we ingest whimsical course data to how runtime chat flows braid SQL, vector, and graph evidence into a single answer. It covers the files under `src/services/` and the surrounding operational docs so new contributors can reason about the entire stack without spelunking every module.

## Introduction

### What is Dandori?
Dandori is the art of managing ones’ resources efficiently, to maximise the output. At the School of Dandori, the resource being managed is time and wellbeing. The philosophy of the school is that we should enjoy our time and look after our wellbeing.

### Who are the School of Dandori?
The School of Dandori teaches wellbeing and encourages people to reconnect with their younger and more carefree days. Exclusively for adults, the School of Dandori offer a range of evening and weekend classes in a delightful range of topics. Each class has an air of whimsy and is designed to encourage people to embrace their most playful nature, to disconnect from the stress of life, and look after their holistic self.

Founded in 2017, at the dawn of a new era in machine intelligence, the school was founded by Ada Calm and Tessa Forman — two technologists who believed that if machines were going to master attention, humans would need to reclaim it. The team at the School of Dandori is very small – just Ada, Tessa, and Arthur Ingham. Ada manages the day to day running of the School of Dandori, with a specialism in the financial management. Tessa manages the go-to-market strategy, and advertising, ensuring that their courses are advertised locally across communities. Arthur built and manages the technology platform that forms the heart of The School of Dandori.

The School of Dandori works with hundreds of freelance course instructors across the United Kingdom who submit and run their whimsical courses. The technology platform allows customers to register and pay for courses, and then sends the instructors the participant list and share of the course fees.

### The project
The School of Dandori, having been founded to reclaim the joy of life from machines, has resisted the use of Generative AI within their organisation. Ada, Tessa, and Arthur believe that now more than ever the School of Dandori is providing an essential service to the people of the United Kindgom – and they wish to scale their offering to onboard new instructors and increase their overall capacity. Facing several key challenges with upscaling, they’ve realised that Artificial Intelligence might hold the key to solving their challenges and bringing good Dandori to a wider audience.

You will be meeting

## 1. North Star

- **Purpose**: Guarantee every AI response is grounded in verifiable course knowledge (database records, vector chunks, graph entities) while staying playful and human.
- **Design pillars**:
  1. *Layered Retrieval*: SQL → vector RAG → GraphRAG, escalated based on mode.
  2. *Deterministic Metadata Hygiene*: Every chunk, triple, or edge carries structured metadata for traceability.
  3. *Configurable Providers*: Vector + graph providers are environment-driven so we can swap backends (Chroma, Qdrant, Vertex AI, Neo4j) without touching business logic.

## 2. Data Inputs & Normalisation

| Source | Notes | Key Implementations |
| ------ | ----- | ------------------- |
| Supabase/Postgres `courses` table | Canonical truth for course attributes. | `ChatService._search_courses()` in `src/services/chat_service.py` performs parameterised SQL with allow-list filters. |
| Uploaded PDF / JSON assets | Parsed elsewhere, but once they reach services they are plain dicts. | Chunk and graph builders call `parse_json_fields()` so nested JSON from Supabase rows becomes typed Python objects. |

Important helper:
- `sanitize_metadata()` in `src/services/base_rag_service.py` keeps metadata JSON-safe by coercing every value to primitives.

## 3. Vector Context Path (`RAGService`)

### 3.1 Chunk construction
- `CourseChunkBuilder` (`src/services/chunk_builder.py`)
  - **Modes**: `simple` (field-by-field atoms) vs `narrative` (stitched story). Graph workflows use `narrative` with `max_chars` to stay under embedding limits.
  - **Metadata contract**: Every chunk metadata includes `course_id`, `class_id`, `title`, `course_type`, `location`, `instructor`, and `cost`. This powers UI tooltips and filtering.

### 3.2 Base service machinery
- `BaseRAGService` handles provider discovery (`VectorStoreFactory`), directory bootstrap for Chroma (`ensure_chroma_persist_dir()`), and batch-safe `add/delete` cycles via `_replace_collection()`.
- Environment knobs:
  - `VECTOR_STORE_PROVIDER` (defaults to `chroma`).
  - `CHROMA_PERSIST_DIR`, `QDRANT_URL`, Vertex AI secrets, etc.—see `docs/API.md` for provider-specific guidance.

### 3.3 Runtime usage
- `RAGService` (`src/services/rag_service.py`)
  - Builds chunks through `CourseChunkBuilder(mode="simple")` today for standard embeddings.
  - `search()` normalises provider output with `_shape_results()` so downstream consumers always see `documents`, `metadatas`, `distances`, `ids`, `count`.

## 4. Graph Context Path (`GraphRAGService`)

### 4.1 Triple + chunk builders
- `build_kg_triples()` + `build_enriched_triples()` in `src/services/graph_builders.py` mine metadata, skills, objectives, materials, and derived analytics (tokens, phrases, theming) into predicate-rich triples like `teaches_concept`, `develops_proficiency_in`, `belongs_to_theme`.
- `build_course_chunks()` reuses `CourseChunkBuilder(mode="narrative")` for hybrid stores; chunk metadata matches the vector format, allowing shared tooling.

### 4.2 Graph store orchestration
- `GraphRAGService` (`src/services/graph_rag_service.py`)
  - Creates two vector stores (KG triples + chunk narratives) and optionally a Neo4j graph via `create_graph_store()`.
  - Environment toggles:
    | Variable | Effect |
    | -------- | ------ |
    | `GRAPH_RAG_KG_COLLECTION` / `GRAPH_RAG_CHUNK_COLLECTION` | Override collection names inside Chroma/Qdrant. |
    | `GRAPH_RAG_USE_NEO4J` | When `true`, instantiates `Neo4jGraphStore`; requires `NEO4J_PASSWORD`.
    | `GRAPH_RAG_NEO4J_BATCH_SIZE` | Controls streaming writes to Neo4j. |
    | `GRAPH_RAG_VECTOR_PROVIDER` | Forces provider used by graph mode regardless of global default. |
  - `index_courses()` writes triples/chunks in batches and, when Neo4j is enabled, mirrors relationships into the graph store for neighbor exploration.

### 4.3 Graph store contracts
- `GraphStore` (`src/services/graph_store.py`) defines `replace_graph()`, `neighbors()`, `get_entity()`. The default registry wires Neo4j via `create_graph_store()` but can register other backends.
- `Neo4jGraphStore` batches deletes/inserts, persists subject/object properties, and exposes directional neighbor lookups that the chat layer surfaces as `Graph context` bullets.

## 5. Chat Runtime & Context Stitching (`ChatService`)

### 5.1 Tool-enforced retrieval
- `ChatService.stream_chat()` is the single entry point for `/chat` requests.
- The system prompt **forces** at least one tool call before an answer. Tools map directly to service methods:
  1. `search_courses` → SQL filterable search.
  2. `semantic_search` → `RAGService.search()`.
  3. `graph_neighbors` → `GraphRAGService.graph_neighbors()` (only in `mode="graphrag"`).
- Tool schemas live in `_tool_schemas()` so OpenAI-compatible models can auto-call them.

### 5.2 Initial context injection
- `_initial_context(query, mode)` seeds the LLM with a fast triage:
  - SQL top-3 course titles.
  - RAG metadata summaries.
  - Optional Graph neighbors (Neo4j-only).
- This message is prepended as a system message, ensuring deterministic grounding even before streaming begins.

### 5.3 Graceful degradation
- Missing API key ➝ falls back to SQL search only, emitting human-readable bullet lists.
- Missing OpenAI SDK ➝ informs client via artifacts (the `display(id)` markers are parsed by `_display_artifacts()` to hydrate UI capsules).

### 5.4 Evidence trail (`examples/`)

To show how context deepens as we escalate from vanilla RAG to GraphRAG to a live Neo4j hop, compare the canned fixtures under `dandori/examples/`:

| Layer | File | What it proves |
| ----- | ---- | -------------- |
| Vector RAG | `examples/rag_moss.json` | Returns only chunk-level prose + metadata (distances, course ids) for `Mystical Moss Mastery`, demonstrating `_shape_results()` structure and how `_distance` scores surface without graph semantics. |
| GraphRAG hybrid | `examples/graphrag_moss.json` | Includes both `chunks` and `kg` payloads for the same “moss” query, showing predicate-rich triples (`teaches_concept`, `is_of_type`) and matching metadata that powers Graph context bullets. |
| Neo4j neighbors | `examples/neo4j_moss.json` | Captures the `graph_neighbors()` response: `entity`, `properties`, and directional `neighbors` with predicates like `provides_material`, validating the deeper inspection layer once `GRAPH_RAG_USE_NEO4J=true`. |

#### Vector RAG payload excerpt (`examples/rag_moss.json`)

```json
{
  "count": 3,
  "results": [
    {
      "_distance": 0.7791299,
      "id": 88,
      "class_id": "CLASS_088",
      "title": "Mystical Moss Mastery",
      "course_type": "Nature Crafts",
      "location": "Peak District",
      "instructor": "Fern Greenleaf",
      "skills": [
        "Botany Craftsmanship Ecological Understanding Mindfulness",
        "Artistic Expression"
      ],
      "learning_objectives": [
        "Identify and differentiate between various types of moss common to the Peak District.",
        "Cultivate and care for moss in artistic terrariums.",
        "Design and create whimsical moss sculptures for home decoration."
      ]
    }
  ]
}
```

#### GraphRAG hybrid payload excerpt (`examples/graphrag_moss.json`)

```json
{
  "chunks": {
    "documents": [
      "Course Title: Magical Moss Mosaics. Course Type: Nature Crafts. Instructor: Professor Lichenbottom. ...",
      "Course Title: Mystical Moss Mosaics. Course Type: Nature Crafts. Instructor: Professor Mossbottom. ..."
    ],
    "metadatas": [
      {
        "chunk_id": "chunk::209",
        "course_id": 209,
        "title": "Magical Moss Mosaics",
        "location": "Edinburgh"
      },
      {
        "chunk_id": "chunk::3",
        "course_id": 3,
        "title": "Mystical Moss Mosaics",
        "location": "Scottish Highlands"
      }
    ]
  },
  "kg": {
    "documents": [
      "Mystical Moss Mastery teaches concept artistic",
      "Magical Moss Mosaics is of type Nature Crafts",
      "Mystical Moss Mosaics is of type Nature Crafts"
    ],
    "metadatas": [
      {
        "predicate": "teaches_concept",
        "subject": "Mystical Moss Mastery",
        "object": "artistic"
      },
      {
        "predicate": "is_of_type",
        "subject": "Magical Moss Mosaics",
        "object": "Nature Crafts"
      }
    ]
  }
}
```

#### Neo4j neighbor payload excerpt (`examples/neo4j_moss.json`)

```json
{
  "entity": "Mystical Moss Mosaics",
  "found": true,
  "properties": {
    "course_id": 3,
    "class_id": "CLASS_003",
    "entity_type": "course",
    "uid": "mystical_moss_mosaics_3"
  },
  "neighbors": [
    {
      "direction": "out",
      "predicate": "teaches_concept",
      "neighbor": "expression",
      "text": "Mystical Moss Mosaics teaches concept expression"
    },
    {
      "direction": "out",
      "predicate": "provides_material",
      "neighbor": "Natural adhesive",
      "text": "Mystical Moss Mosaics provides material Natural adhesive"
    }
  ]
}
```

Use these snapshots when QA’ing regressions: run the same query locally and diff against the JSON to confirm we still honor the expected `rag < graphrag < neo4j` fidelity ladder.

## 6. Service Factory & Extensibility

- `src/services/__init__.py` exposes `get_service(mode="vector"|"graph")` so CLI scripts (`scripts/reindex_services.py`) and API routes can request the appropriate backend without caring about implementation specifics.
- When adding new retrieval modes (e.g., Hybrid-BM25), follow the same shape:
  1. Subclass `BaseRAGService`.
  2. Register provider-specific knobs via env vars.
  3. Extend `get_service()` with a new literal choice.

## 7. Operational Playbook

1. **Reindexing**: Run `python scripts/reindex_services.py --mode both` after touching ingestion logic. This rebuilds vector + graph stores.
2. **Verification**:
   - Vector mode: `curl /api/search` with a sample query.
   - Graph mode: `curl /api/graph-search` or hit the `/chat` UI in `graphrag` mode and ensure `Graph context` bullets appear.
3. **Monitoring**:
   - Watch `api_logger` output (`GraphRAGService` logs Neo4j config redactions).
   - Neo4j neighbors returning `{"error": "Neo4j neighbors are disabled"}` signals missing env or driver; fix before enabling graph UI.

## 8. Future Enhancements

| Idea | Motivation | Notes |
| ---- | ---------- | ----- |
| Context window budgeting | Dynamically cap `initial_context` snippets based on model context. | Hook into `_initial_context()` after counting tokens. |
| Metadata lineage | Attach ingestion timestamps + source filenames into chunk/triple metadata for better audit trails. | Update `sanitize_metadata()` call sites. |
| Pluggable graph backends | Register `memgraph`/`nebula` factories via `register_graph_backend()`. | Only needs new `GraphStore` implementations. |

---

Use this playbook when onboarding contributors, reviewing PRs that touch retrieval, or planning experiments (chunking strategies, providers, or prompt flows). It centralises everything currently scattered across `docs/` and `src/services/` into one context engineering narrative.
