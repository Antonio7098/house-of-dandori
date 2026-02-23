#!/usr/bin/env python3
"""
School of Dandori - Course API Server (Entry Point)
Exposes course data via REST API
"""

from src.api.app import create_app
from src.core.utils import parse_json_fields
from src.models.database import get_db_connection
from src.services.rag_service import get_rag_service

app = create_app()


def reindex_on_startup():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

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
