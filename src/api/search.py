import os
from flask import Blueprint, jsonify, request

from src.core.utils import parse_json_fields
from src.models.database import get_db_connection

search_bp = Blueprint("search", __name__)


@search_bp.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(
        {
            "vectorIndexingEnabled": os.environ.get(
                "ENABLE_VECTOR_INDEXING", "true"
            ).lower()
            == "true"
        }
    )


rag_service = None


def get_rag():
    global rag_service
    if rag_service is None:
        from src.services.rag_service import get_rag_service

        provider = request.args.get("provider")
        rag_service = get_rag_service(provider)
    return rag_service


@search_bp.route("/api/search", methods=["GET"])
def semantic_search():
    query = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("n", 10))
    offset = (page - 1) * limit

    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    try:
        rag = get_rag()
        results = rag.search(query, n_results=limit + offset)

        course_ids = []
        if results.get("ids") and results["ids"][0]:
            course_ids = [int(id.split("_")[0]) for id in results["ids"][0]]

        total = len(course_ids)
        paginated_ids = course_ids[offset : offset + limit]

        if not paginated_ids:
            return jsonify(
                {
                    "results": [],
                    "count": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit,
                }
            )

        conn = get_db_connection()
        cursor = conn.cursor()
        from src.core.config import DATABASE_URL

        use_postgres = bool(DATABASE_URL)
        placeholder = "%s" if use_postgres else "?"

        placeholders = ",".join([placeholder] * len(paginated_ids))
        cursor.execute(
            f"SELECT * FROM courses WHERE id IN ({placeholders})", paginated_ids
        )
        courses = {c["id"]: parse_json_fields(c) for c in cursor.fetchall()}
        conn.close()

        ordered_results = []
        for i, course_id in enumerate(paginated_ids):
            if course_id in courses:
                course = courses[course_id]
                real_idx = offset + i
                course["_distance"] = (
                    results["distances"][0][real_idx]
                    if results.get("distances")
                    else None
                )
                ordered_results.append(course)

        return jsonify(
            {
                "results": ordered_results,
                "count": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@search_bp.route("/api/index", methods=["POST"])
def index_courses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

        if not courses:
            return jsonify({"message": "No courses to index", "count": 0})

        rag = get_rag()
        rag.index_courses(courses)
        return jsonify({"message": "Courses indexed", "count": len(courses)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@search_bp.route("/api/reindex", methods=["POST"])
def reindex_courses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

        if not courses:
            return jsonify({"message": "No courses to index", "count": 0})

        rag = get_rag()
        chunks = rag.build_chunks(courses)
        if chunks:
            rag.vector_store.delete([c["id"] for c in chunks])

        rag.index_courses(courses)
        return jsonify(
            {"message": "Vector store wiped and re-indexed", "count": len(courses)}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
