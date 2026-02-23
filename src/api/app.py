from flask import Flask, jsonify, render_template

from src.api.routes import courses_bp
from src.api.search import search_bp


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

    return app
