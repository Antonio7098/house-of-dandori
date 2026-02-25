#!/usr/bin/env python3
"""
School of Dandori - Course API Server (Entry Point)
Exposes course data via REST API
"""

import os

from src.api.app import create_app
from src.core.utils import parse_json_fields
from src.models.database import get_db_connection
from src.services.rag_service import get_rag_service

app = create_app()


def reindex_on_startup():
    env = os.environ.get("ENVIRONMENT", "development").lower()
    enabled = os.environ.get("REINDEX_ON_STARTUP", "true").lower() == "true"
    max_courses = os.environ.get("REINDEX_MAX_COURSES")
    sample_size: int | None = None
    if max_courses:
        try:
            sample_size = max(1, int(max_courses))
        except ValueError:
            sample_size = None

    # Set default provider based on environment (can still be overridden by VECTOR_STORE_PROVIDER env)
    if env == "production":
        os.environ.setdefault("VECTOR_STORE_PROVIDER", "vertexai")
        print(
            "Production mode: defaulting to Vertex AI Vector Search (no startup reindex needed)"
        )
        return
    else:
        os.environ.setdefault("VECTOR_STORE_PROVIDER", "chroma")

    if not enabled:
        print("Startup reindex disabled via REINDEX_ON_STARTUP")
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

        if sample_size and len(courses) > sample_size:
            courses = courses[:sample_size]
            print(f"Startup indexing limited to {sample_size} courses")

        if courses:
            rag = get_rag_service()
            print(f"Indexing {len(courses)} courses on startup...")
            rag.index_courses(courses)
            print(f"Indexed {len(courses)} courses")
    except Exception as e:
        print(f"Startup indexing failed: {e}")


if __name__ == "__main__":
    reindex_on_startup()
    app.run(host="0.0.0.0", port=5000, debug=True)
