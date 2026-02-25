import os
from flask import Blueprint, jsonify, request

from src.core.utils import parse_json_fields
from src.core.errors import BadRequestError, handle_exception
from src.core.logging import api_logger
from src.core.auth import require_auth
from src.models.database import get_db_connection
from src.models.schemas import SearchQuery

search_bp = Blueprint("search", __name__)


@search_bp.route("/api/config", methods=["GET"])
def get_config():
    from src.core.config import ENVIRONMENT, DEV_BYPASS_AUTH, SUPABASE_URL

    return jsonify(
        {
            "environment": ENVIRONMENT,
            "vectorStoreProvider": os.environ.get("VECTOR_STORE_PROVIDER", "chroma"),
            "authEnabled": not DEV_BYPASS_AUTH,
            "supabaseConfigured": bool(SUPABASE_URL),
            "graphNeighborsEnabled": os.environ.get("GRAPH_RAG_USE_NEO4J", "false").lower()
            == "true",
        }
    )


rag_service = None
graph_rag_service = None
graph_rag_provider = None


def get_rag():
    global rag_service
    if rag_service is None:
        from src.services.rag_service import get_rag_service

        provider = request.args.get("provider")
        rag_service = get_rag_service(provider)
    return rag_service


def get_graph_rag():
    global graph_rag_service, graph_rag_provider
    provider = request.args.get("provider")
    if graph_rag_service is None or (provider and provider != graph_rag_provider):
        from src.services.graph_rag_service import get_graph_rag_service

        graph_rag_service = get_graph_rag_service(provider)
        graph_rag_provider = provider
    return graph_rag_service


@search_bp.route("/api/search", methods=["GET"])
def semantic_search():
    query = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("n", 10))
    offset = (page - 1) * limit

    if not query:
        error_dict, status_code = handle_exception(
            BadRequestError("Query parameter 'q' is required")
        )
        return jsonify(error_dict), status_code

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

        use_postgres = bool(os.environ.get("DATABASE_URL"))
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

        api_logger.log_request(
            method="GET",
            path="/api/search",
            status_code=200,
            duration_ms=0,
            params={"q": query, "page": page, "n": limit},
        )
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
        api_logger.log_error(e, {"path": "/api/search", "method": "GET"})
        error_dict, status_code = handle_exception(e)
        return jsonify(error_dict), status_code


@search_bp.route("/api/graph-search", methods=["GET"])
def graph_search():
    query = request.args.get("q", "")
    k_kg = int(request.args.get("k_kg", 5))
    k_chunks = int(request.args.get("k_chunks", 5))

    if not query:
        error_dict, status_code = handle_exception(
            BadRequestError("Query parameter 'q' is required")
        )
        return jsonify(error_dict), status_code

    try:
        graph_rag = get_graph_rag()
        
        results = graph_rag.hybrid_search(
            query=query,
            k_kg=k_kg,
            k_chunks=k_chunks,
        )
        
        api_logger.log_request(
            method="GET",
            path="/api/graph-search",
            status_code=200,
            duration_ms=0,
            params={
                "q": query,
                "k_kg": k_kg,
                "k_chunks": k_chunks,
            },
        )
        return jsonify(results)

    except Exception as e:
        api_logger.log_error(e, {"path": "/api/graph-search", "method": "GET"})
        error_dict, status_code = handle_exception(e)
        return jsonify(error_dict), status_code


@search_bp.route("/api/graph-neighbors", methods=["GET"])
def graph_neighbors():
    value = request.args.get("value", "").strip()
    limit = int(request.args.get("limit", 25))

    if not value:
        error_dict, status_code = handle_exception(
            BadRequestError("Query parameter 'value' is required")
        )
        return jsonify(error_dict), status_code

    try:
        graph_rag = get_graph_rag()
        if not getattr(graph_rag, "neo4j_enabled", False) or not graph_rag.neo4j_store:
            raise BadRequestError(
                "Graph neighbors require Neo4j. Set GRAPH_RAG_USE_NEO4J=true with valid credentials."
            )

        neighbors = graph_rag.graph_neighbors(value=value, limit=limit)
        api_logger.log_request(
            method="GET",
            path="/api/graph-neighbors",
            status_code=200,
            duration_ms=0,
            params={"value": value, "limit": limit},
        )
        return jsonify(neighbors)
    except Exception as e:
        api_logger.log_error(e, {"path": "/api/graph-neighbors", "method": "GET"})
        error_dict, status_code = handle_exception(e)
        return jsonify(error_dict), status_code


@search_bp.route("/api/index", methods=["POST"])
@require_auth
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
        api_logger.log_request(
            method="POST",
            path="/api/index",
            status_code=200,
            duration_ms=0,
            count=len(courses),
        )
        return jsonify({"message": "Courses indexed", "count": len(courses)})
    except Exception as e:
        api_logger.log_error(e, {"path": "/api/index", "method": "POST"})
        error_dict, status_code = handle_exception(e)
        return jsonify(error_dict), status_code


@search_bp.route("/api/graph-index", methods=["POST"])
@require_auth
def graph_index_courses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

        if not courses:
            return jsonify({"message": "No courses to index", "count": 0})

        limit_param = request.args.get("limit")
        course_limit: Optional[int] = None
        if limit_param:
            try:
                course_limit = max(1, int(limit_param))
            except ValueError:
                raise BadRequestError("Query parameter 'limit' must be an integer")

        if course_limit and len(courses) > course_limit:
            courses = courses[:course_limit]

        graph_rag = get_graph_rag()
        counts = graph_rag.index_courses(courses)

        api_logger.log_request(
            method="POST",
            path="/api/graph-index",
            status_code=200,
            duration_ms=0,
            count=len(courses),
            params={"limit": course_limit} if course_limit else None,
        )
        return jsonify(
            {
                "message": "GraphRAG collections indexed",
                "counts": counts,
                "course_limit": course_limit,
            }
        )
    except Exception as e:
        api_logger.log_error(e, {"path": "/api/graph-index", "method": "POST"})
        error_dict, status_code = handle_exception(e)
        return jsonify(error_dict), status_code


@search_bp.route("/api/reindex", methods=["POST"])
@require_auth
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
        api_logger.log_request(
            method="POST",
            path="/api/reindex",
            status_code=200,
            duration_ms=0,
            count=len(courses),
        )
        return jsonify(
            {"message": "Vector store wiped and re-indexed", "count": len(courses)}
        )
    except Exception as e:
        api_logger.log_error(e, {"path": "/api/reindex", "method": "POST"})
        error_dict, status_code = handle_exception(e)
        return jsonify(error_dict), status_code
