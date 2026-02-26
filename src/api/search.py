import json
import os
from flask import Blueprint, Response, jsonify, request
from typing import Optional

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
    provider_override = request.args.get("provider")
    desired_provider = provider_override or os.environ.get("VECTOR_STORE_PROVIDER")
    current_provider = getattr(rag_service, "provider_name", None)

    if rag_service is None or (
        desired_provider and current_provider != desired_provider
    ):
        from src.services.rag_service import get_rag_service

        rag_service = get_rag_service(desired_provider)
    return rag_service


def get_graph_rag():
    global graph_rag_service, graph_rag_provider
    provider_override = request.args.get("provider")
    env_provider = os.environ.get("GRAPH_RAG_VECTOR_PROVIDER", "chroma")
    provider = provider_override or env_provider

    if graph_rag_service is None or provider != graph_rag_provider:
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

        course_ids: list[int] = []
        metadatas = results.get("metadatas") or []
        if metadatas and isinstance(metadatas[0], list):
            metadata_rows = metadatas[0]
        else:
            metadata_rows = metadatas

        for metadata in metadata_rows:
            if not isinstance(metadata, dict):
                continue
            course_id = metadata.get("course_id")
            if course_id is None:
                continue
            try:
                course_ids.append(int(course_id))
            except (TypeError, ValueError):
                continue

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
        distances = results.get("distances") or []
        if distances and isinstance(distances[0], list):
            distance_list = distances[0]
        else:
            distance_list = distances

        for i, course_id in enumerate(paginated_ids):
            if course_id in courses:
                course = courses[course_id]
                real_idx = offset + i
                course["_distance"] = (
                    distance_list[real_idx]
                    if real_idx < len(distance_list)
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
        # Fallback to SQL text search when vector tooling is unavailable locally.
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            use_postgres = bool(os.environ.get("DATABASE_URL"))
            placeholder = "%s" if use_postgres else "?"
            if use_postgres:
                where = (
                    "title ILIKE %s OR class_id ILIKE %s OR description ILIKE %s "
                    "OR instructor ILIKE %s OR location ILIKE %s OR course_type ILIKE %s"
                )
            else:
                where = (
                    "title LIKE ? OR class_id LIKE ? OR description LIKE ? "
                    "OR instructor LIKE ? OR location LIKE ? OR course_type LIKE ?"
                )
            pattern = f"%{query}%"
            params = [pattern, pattern, pattern, pattern, pattern, pattern]
            cursor.execute(f"SELECT COUNT(*) FROM courses WHERE {where}", params)
            count_row = cursor.fetchone()
            total = count_row[0] if count_row else 0

            cursor.execute(
                f"SELECT * FROM courses WHERE {where} ORDER BY id LIMIT {placeholder} OFFSET {placeholder}",
                [*params, limit, offset],
            )
            courses = [parse_json_fields(c) for c in cursor.fetchall()]
            conn.close()

            return jsonify(
                {
                    "results": courses,
                    "count": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit,
                    "fallback": "sql",
                }
            )
        except Exception:
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
        graph_store = getattr(graph_rag, "graph_store", None)
        if not getattr(graph_rag, "neo4j_enabled", False) or not graph_store:
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


@search_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    stream = bool(data.get("stream"))

    try:
        from src.services.chat_service import chat_service

        if stream:
            def sse_stream():
                for event_name, payload in chat_service.stream_chat(data):
                    yield f"event: {event_name}\n"
                    yield f"data: {json.dumps(payload)}\n\n"

            return Response(sse_stream(), mimetype="text/event-stream")

        final_message = ""
        artifacts = []
        mode = data.get("mode") or "standard"
        model = None
        tool_events = []
        for event_name, payload in chat_service.stream_chat(data):
            if event_name == "text_delta":
                final_message += payload.get("delta", "")
            elif event_name == "message_end":
                final_message = payload.get("message", final_message)
                artifacts = payload.get("artifacts", [])
                mode = payload.get("mode", mode)
                model = payload.get("model")
            elif event_name in {"tool_call", "tool_result", "error"}:
                tool_events.append({"event": event_name, **payload})

        return jsonify({
            "message": final_message,
            "artifacts": artifacts,
            "tool_events": tool_events,
            "mode": mode,
            "model": model,
        })
    except Exception as e:
        api_logger.log_error(e, {"path": "/api/chat", "method": "POST"})
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
