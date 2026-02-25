# Neo4j GraphRAG Guide

This document captures how the School of Dandori backend uses Neo4j to power GraphRAG queries, along with the optimisations introduced during the Feb 2026 iteration (chunk trimming, noise filtering, and capped indexing).

## 1. Architecture Overview

```
Courses DB  ──► GraphRAGService.index_courses()
                ├─ build_kg_triples()    ──► Chroma collection: graph_kg_triples
                ├─ build_course_chunks() ──► Chroma collection: graph_course_chunks
                └─ build_graph_relationships() ──► Neo4j (when GRAPH_RAG_USE_NEO4J=true)
```

* `src/services/graph_rag_service.py` orchestrates KG/chunk construction and optional Neo4j writes.
* `src/services/neo4j_graph_store.py` wraps the official driver to clear + batch-write relationships and expose a `neighbors()` traversal used by `/api/graph-neighbors`.
* `src/api/search.py` exposes the endpoints:
  * `POST /api/graph-index` – triggers the full GraphRAG indexing pipeline (supports `?limit=N`).
  * `GET /api/graph-search` – returns Chroma KG + chunk hits for a query.
  * `GET /api/graph-neighbors` – inspects the Neo4j graph around a value or UID.

## 2. Environment & Defaults

Most knobs now ship with sensible in-code defaults, so the only env you generally need is:

| Variable | Purpose | Default |
| --- | --- | --- |
| `GRAPH_RAG_USE_NEO4J` | Toggle Neo4j persistence | `false` |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Auth when Neo4j is enabled | `bolt://localhost:7687`, `neo4j`, *(required)* |

Everything else (collection names, batch sizes, 2 000-char chunk cap, 500 rel batch) lives directly in `GraphRAGService`, so there is no need to copy a huge env block.

### Disk Management

* `ensure_chroma_persist_dir()` auto-creates `./chroma_data` if no `CHROMA_PERSIST_DIR` override is provided.
* `GRAPH_RAG_MAX_CHUNK_CHARS` (now a constant) trims narrative chunks to 2 000 characters and appends an ellipsis, preventing multi-GB Chroma stores during development.
* The `limit` query parameter on `/api/graph-index` lets you reindex, e.g., 25 % (110 courses) or 50 % (215 courses) without touching the rest of the catalog.

## 3. Optimisations & Refinements

### 3.1 Chunk + Token Quality

| Change | File | Impact |
| --- | --- | --- |
| Added `MAX_CHUNK_CHARS = 2000` | `graph_rag_service.py` | Keeps `chroma_data/` < 5 GB when iterating. |
| Expanded `NOISE_TOKENS` (learn, journey, class, etc.) + better lemmatisation | `graph_rag_service.py` | Removes meaningless `teaches_concept` nodes from Neo4j neighbors. |
| Serialized metadata as JSON before writing to Neo4j | `graph_rag_service.py` & `neo4j_graph_store.py` | Prevents Neo4j driver errors about primitive properties and enables rich neighbor payloads. |

### 3.2 Operational Controls

* `/api/graph-index?limit=N` – added limit handling plus logging so you can reindex slices of the catalog quickly.
* `GRAPH_RAG_USE_NEO4J` – guards all Neo4j interactions; local dev can stay Chroma-only.
* Restarting Neo4j (`docker start dandori-neo4j`) is the only prerequisite before running the indexer; the service will clear and repopulate the graph per run.

## 4. Testing Flow

1. `docker start dandori-neo4j` (if graph mode is on).
2. `python app.py` (or gunicorn) – reindexing on startup is disabled by default, so use manual curls:
   * `curl -X POST http://127.0.0.1:5000/api/graph-index?limit=200`
   * `curl http://127.0.0.1:5000/api/graph-search?q=Creative%20cooking`
   * `curl http://127.0.0.1:5000/api/graph-neighbors?value=Majestic%20Marmalade%20Mastery`
3. Check `du -sh chroma_data` to confirm the store remains below the 5 GB target.

## 5. Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `ServiceUnavailable: Couldn't connect to localhost:7687` | Neo4j container stopped | `docker start dandori-neo4j` |
| Chroma directory ballooning beyond 5 GB | Huge descriptions or full-catalog indexing | Rerun with smaller `limit`, rely on chunk cap, or delete `chroma_data/` before reindexing |
| Neighbor results contain generic tokens (`journey`, `class`) | Stopwords not trimmed | Already handled by extended `NOISE_TOKENS`; rerun `/api/graph-index` to regenerate graph |

For more background, see `README.md` (GraphRAG overview) and `ARCHITECTURE.md` (endpoint matrix + env table).
