import base64
import os

from flask import Flask, jsonify, make_response, render_template, request

from src.api.routes import courses_bp
from src.api.search import search_bp
from src.api.auth import auth_bp
from src.core.errors import AppError, handle_exception
from src.core.logging import api_logger
from src.core.config import SUPABASE_URL, SUPABASE_ANON_KEY


FAVICON_BYTES = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")


def create_app():
    app = Flask(__name__, template_folder="../../templates")
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB

    allowed_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ] or ["*"]

    def _resolve_origin(request_origin: str | None) -> str | None:
        if "*" in allowed_origins:
            return request_origin or "*"
        if request_origin and request_origin in allowed_origins:
            return request_origin
        return None

    def _apply_cors_headers(response):
        origin = request.headers.get("Origin")
        allowed_origin = _resolve_origin(origin)
        if allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers.setdefault("Vary", "Origin")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        return response

    @app.before_request
    def _handle_preflight():
        if request.method == "OPTIONS":
            response = make_response("", 204)
            return _apply_cors_headers(response)

    @app.after_request
    def _apply_cors(response):
        return _apply_cors_headers(response)

    app.register_blueprint(courses_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(auth_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login")
    def login():
        return render_template("login.html")

    @app.route("/signup")
    def signup():
        return render_template("signup.html")

    @app.route("/profile")
    def profile():
        return render_template("profile.html")

    @app.route("/auth/callback")
    def auth_callback():
        return render_template("callback.html")

    @app.route("/favicon.ico")
    def favicon():
        response = make_response(FAVICON_BYTES)
        response.headers.set("Content-Type", "image/gif")
        return response

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"})

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception):
        api_logger.log_error(error, {"path": request.path})
        error_dict, status_code = handle_exception(error)
        return jsonify(error_dict), status_code

    return app
