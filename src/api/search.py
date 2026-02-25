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
    include_answer = request.args.get("answer", "false").lower() == "true"
    
    # Get filters
    location = request.args.get("location", "")
    course_type = request.args.get("course_type", "")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    sort_by = request.args.get("sort_by", "")

    if not query:
        error_dict, status_code = handle_exception(
            BadRequestError("Query parameter 'q' is required")
        )
        return jsonify(error_dict), status_code

    try:
        from src.services.graph_rag_service import get_graph_rag_service
        provider = request.args.get("provider")
        graph_rag = get_graph_rag_service(provider)
        
        # Parse filters
        filters = {}
        if location:
            filters["location"] = location
        if course_type:
            filters["course_type"] = course_type
        
        try:
            if min_price and min_price != 'undefined':
                filters["min_price"] = float(min_price)
            if max_price and max_price != 'undefined':
                filters["max_price"] = float(max_price)
        except ValueError:
            pass
            
        if sort_by:
            filters["sort_by"] = sort_by
            
        results = graph_rag.hybrid_search(
            query=query,
            k_kg=k_kg,
            k_chunks=k_chunks,
            include_answer=include_answer,
            filters=filters
        )
        
        # The hybrid search in graph_rag_service might not implement filtering or sorting yet.
        # We need to manually filter and sort the courses in the results if it didn't
        if "courses" in results and results["courses"]:
            courses = results["courses"]
            
            # Post-filtering
            filtered_courses = []
            for c in courses:
                # Filter by location
                if location and location.lower() not in c.get("location", "").lower():
                    continue
                # Filter by course type
                if course_type and course_type.lower() not in c.get("course_type", "").lower():
                    continue
                
                # Filter by price
                try:
                    cost_str = c.get("cost", "£0").replace("£", "").strip()
                    cost = float(cost_str) if cost_str else 0.0
                    
                    if min_price and min_price != 'undefined' and cost < float(min_price):
                        continue
                    if max_price and max_price != 'undefined' and cost > float(max_price):
                        continue
                except (ValueError, TypeError):
                    pass
                    
                filtered_courses.append(c)
                
            # Sorting
            if sort_by == 'price_asc':
                filtered_courses.sort(key=lambda c: float(c.get("cost", "£0").replace("£", "").strip() or 0))
            elif sort_by == 'price_desc':
                filtered_courses.sort(key=lambda c: float(c.get("cost", "£0").replace("£", "").strip() or 0), reverse=True)
            elif sort_by == 'newest':
                filtered_courses.sort(key=lambda c: c.get("created_at", ""), reverse=True)
                
            results["courses"] = filtered_courses
            results["count"] = len(filtered_courses)
        
        api_logger.log_request(
            method="GET",
            path="/api/graph-search",
            status_code=200,
            duration_ms=0,
            params={
                "q": query,
                "k_kg": k_kg,
                "k_chunks": k_chunks,
                "answer": include_answer
            },
        )
        return jsonify(results)

    except Exception as e:
        api_logger.log_error(e, {"path": "/api/graph-search", "method": "GET"})
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

        from src.services.graph_rag_service import get_graph_rag_service
        graph_rag = get_graph_rag_service()
        counts = graph_rag.index_courses(courses)
        
        api_logger.log_request(
            method="POST",
            path="/api/graph-index",
            status_code=200,
            duration_ms=0,
            count=len(courses),
        )
        return jsonify({"message": "GraphRAG collections indexed", "counts": counts})
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
