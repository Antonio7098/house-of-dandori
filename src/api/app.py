from flask import Flask, jsonify, render_template, request, send_from_directory
import os

try:
    from flask_cors import CORS
except Exception:  # pragma: no cover - optional dependency fallback
    CORS = None

from src.api.routes import courses_bp
from src.api.search import search_bp
from src.api.auth import auth_bp
from src.api.user import user_bp
from src.api.chat import chat_bp
from src.core.errors import AppError, handle_exception
from src.core.logging import api_logger
from src.core.config import SUPABASE_URL, SUPABASE_ANON_KEY

# Path to the built frontend
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), '../../frontend/dist')


def create_app():
    app = Flask(__name__, 
                template_folder="../../templates",
                static_folder=FRONTEND_DIST,
                static_url_path='/static')
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB
    
    # Enable CORS for all routes when flask-cors is installed
    if CORS is not None:
        CORS(app)

    # Register API blueprints FIRST so they take precedence
    app.register_blueprint(courses_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(chat_bp)

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"})

    @app.route("/")
    def index():
        response = send_from_directory(FRONTEND_DIST, 'index.html')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    @app.route("/assets/<path:filename>")
    def serve_assets(filename):
        return send_from_directory(os.path.join(FRONTEND_DIST, 'assets'), filename)

    @app.route("/<path:path>")
    def serve_frontend(path):
        # Don't intercept API routes
        if path.startswith('api/'):
            return jsonify({"error": "Not found"}), 404
        # Serve static files if they exist, otherwise serve index.html for SPA routing
        file_path = os.path.join(FRONTEND_DIST, path)
        if os.path.isfile(file_path):
            return send_from_directory(FRONTEND_DIST, path)
        response = send_from_directory(FRONTEND_DIST, 'index.html')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception):
        api_logger.log_error(error, {"path": request.path})
        error_dict, status_code = handle_exception(error)
        return jsonify(error_dict), status_code

    return app
