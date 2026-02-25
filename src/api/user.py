from flask import Blueprint, request, jsonify
import os
from src.core.auth import auth_service
from src.core.errors import handle_exception, BadRequestError, NotFoundError, DatabaseError
from src.models.database import get_db_connection
from src.core.logging import api_logger

user_bp = Blueprint("user", __name__)

def get_placeholder():
    return "%s" if os.environ.get("DATABASE_URL") else "?"

@user_bp.route("/api/user/saved-courses", methods=["GET"])
def get_saved_courses():
    token = auth_service.get_token_from_header()
    if not token and not auth_service.dev_bypass:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        user = auth_service.verify_token(token) if not auth_service.dev_bypass else {"id": "dev_user"}
        user_id = user["id"]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ph = get_placeholder()
        cursor.execute(f"SELECT course_id FROM saved_courses WHERE user_id = {ph}", (user_id,))
        rows = cursor.fetchall()
        course_ids = [row["course_id"] if isinstance(row, dict) else row[0] for row in rows]
        
        conn.close()
        return jsonify(course_ids)
    except Exception as e:
        api_logger.log_error(e, {"user_id": user_id if 'user_id' in locals() else None})
        error_dict, status_code = handle_exception(DatabaseError("Failed to fetch saved courses"))
        return jsonify(error_dict), status_code

@user_bp.route("/api/user/saved-courses", methods=["POST"])
def save_course():
    token = auth_service.get_token_from_header()
    if not token and not auth_service.dev_bypass:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    course_id = data.get("course_id")
    
    if not course_id:
        error_dict, status_code = handle_exception(BadRequestError("Course ID required"))
        return jsonify(error_dict), status_code
        
    try:
        user = auth_service.verify_token(token) if not auth_service.dev_bypass else {"id": "dev_user"}
        user_id = user["id"]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ph = get_placeholder()
        if os.environ.get("DATABASE_URL"):
            cursor.execute(
                f"INSERT INTO saved_courses (user_id, course_id) VALUES ({ph}, {ph}) ON CONFLICT DO NOTHING",
                (user_id, course_id)
            )
        else:
            cursor.execute(
                f"INSERT OR IGNORE INTO saved_courses (user_id, course_id) VALUES ({ph}, {ph})",
                (user_id, course_id)
            )
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Course saved successfully"}), 201
    except Exception as e:
        api_logger.log_error(e, {"user_id": user_id if 'user_id' in locals() else None, "course_id": course_id})
        error_dict, status_code = handle_exception(DatabaseError("Failed to save course"))
        return jsonify(error_dict), status_code

@user_bp.route("/api/user/saved-courses/<course_id>", methods=["DELETE"])
def unsave_course(course_id):
    token = auth_service.get_token_from_header()
    if not token and not auth_service.dev_bypass:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        user = auth_service.verify_token(token) if not auth_service.dev_bypass else {"id": "dev_user"}
        user_id = user["id"]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ph = get_placeholder()
        cursor.execute(
            f"DELETE FROM saved_courses WHERE user_id = {ph} AND course_id = {ph}",
            (user_id, course_id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Course removed from saved"}), 200
    except Exception as e:
        api_logger.log_error(e, {"user_id": user_id if 'user_id' in locals() else None, "course_id": course_id})
        error_dict, status_code = handle_exception(DatabaseError("Failed to unsave course"))
        return jsonify(error_dict), status_code

@user_bp.route("/api/courses/<course_id>/reviews", methods=["GET"])
def get_course_reviews(course_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ph = get_placeholder()
        cursor.execute(f"""
            SELECT r.*, p.name as user_name 
            FROM reviews r 
            LEFT JOIN profiles p ON r.user_id = p.user_id 
            WHERE r.course_id = {ph} 
            ORDER BY r.created_at DESC
        """, (course_id,))
        
        reviews = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({"reviews": reviews})
    except Exception as e:
        api_logger.log_error(e, {"course_id": course_id})
        error_dict, status_code = handle_exception(DatabaseError("Failed to fetch reviews"))
        return jsonify(error_dict), status_code

@user_bp.route("/api/courses/<course_id>/reviews", methods=["POST"])
def add_review(course_id):
    token = auth_service.get_token_from_header()
    if not token and not auth_service.dev_bypass:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    rating = data.get("rating")
    review = data.get("review", "")
    
    if not rating or not (1 <= rating <= 5):
        error_dict, status_code = handle_exception(BadRequestError("Rating must be between 1 and 5"))
        return jsonify(error_dict), status_code
        
    try:
        user = auth_service.verify_token(token) if not auth_service.dev_bypass else {"id": "dev_user"}
        user_id = user["id"]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ph = get_placeholder()
        if os.environ.get("DATABASE_URL"):
            cursor.execute(
                f"""
                INSERT INTO reviews (user_id, course_id, rating, review) 
                VALUES ({ph}, {ph}, {ph}, {ph})
                ON CONFLICT(user_id, course_id) DO UPDATE SET
                    rating = EXCLUDED.rating,
                    review = EXCLUDED.review,
                    created_at = CURRENT_TIMESTAMP
                """,
                (user_id, course_id, rating, review)
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO reviews (user_id, course_id, rating, review) 
                VALUES ({ph}, {ph}, {ph}, {ph})
                ON CONFLICT(user_id, course_id) DO UPDATE SET
                    rating = excluded.rating,
                    review = excluded.review,
                    created_at = CURRENT_TIMESTAMP
                """,
                (user_id, course_id, rating, review)
            )
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Review added successfully"}), 201
    except Exception as e:
        api_logger.log_error(e, {"user_id": user_id if 'user_id' in locals() else None, "course_id": course_id})
        error_dict, status_code = handle_exception(DatabaseError("Failed to add review"))
        return jsonify(error_dict), status_code
