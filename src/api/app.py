from flask import Flask, jsonify, render_template, request

from src.api.routes import courses_bp
from src.api.search import search_bp
from src.core.errors import AppError, handle_exception
from src.core.logging import api_logger


def create_app():
    app = Flask(__name__, template_folder="../../templates")
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB

    app.register_blueprint(courses_bp)
    app.register_blueprint(search_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

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
