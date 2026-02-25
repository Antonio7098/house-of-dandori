#!/usr/bin/env python3
"""Utility script to rebuild vector and graph indices from the courses table."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.utils import parse_json_fields
from src.models.database import get_db_connection
from src.services import get_service
from src.services.base_rag_service import ensure_chroma_persist_dir


def load_courses(limit: Optional[int] = None) -> List[dict]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        rows = cursor.fetchall()
    finally:
        conn.close()

    courses = [parse_json_fields(row) for row in rows]
    if limit:
        courses = courses[:limit]
    return courses


def index_vector(courses: List[dict], provider: Optional[str]) -> int:
    service = get_service("vector", provider=provider)
    try:
        service.index_courses(courses)
    finally:
        service.close()
    return len(courses)


def index_graph(courses: List[dict], provider: Optional[str]) -> Dict[str, Any]:
    service = get_service("graph", provider=provider)
    try:
        return service.index_courses(courses)
    finally:
        service.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild vector and/or graph indices from the courses table"
    )
    parser.add_argument(
        "--mode",
        choices=("vector", "graph", "both"),
        default="both",
        help="Which services to reindex",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional cap on number of courses to index",
    )
    parser.add_argument(
        "--provider",
        help="Override VECTOR_STORE_PROVIDER when instantiating services",
    )
    args = parser.parse_args()

    courses = load_courses(args.limit)
    if not courses:
        print("No courses found to index", file=sys.stderr)
        sys.exit(1)

    mode = args.mode
    provider = args.provider

    if mode in ("vector", "both"):
        count = index_vector(courses, provider)
        print(f"Indexed {count} chunks into the vector store")

    if mode in ("graph", "both"):
        counts = index_graph(courses, provider)
        print("Graph indexing counts:")
        for key, value in counts.items():
            print(f"  - {key}: {value}")


if __name__ == "__main__":
    os.environ.setdefault("VECTOR_STORE_PROVIDER", "chroma")
    os.environ.setdefault("CHROMA_PERSIST_DIR", ensure_chroma_persist_dir())
    main()
