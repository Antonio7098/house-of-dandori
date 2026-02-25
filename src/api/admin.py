from flask import Blueprint, request, jsonify
from src.core.auth import auth_service
from src.core.errors import handle_exception, BadRequestError, NotFoundError, DatabaseError
from src.models.database import get_db_connection
from src.core.logging import api_logger

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/api/admin/courses", methods=["GET"])
@admin_bp.route("/api/admin/courses/<int:course_id>", methods=["DELETE"])
def admin_courses():
    pass
