#!/usr/bin/env python3
"""
School of Dandori - Course API Server
Exposes course data via REST API
"""

import io
import os
import re
import sqlite3
import uuid
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import psycopg2
from psycopg2 import extras
from flask import Flask, jsonify, request, render_template, send_file
from werkzeug.utils import secure_filename
import PyPDF2

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

DB_PATH = os.environ.get("DB_PATH", "courses.db")
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = "".join(DATABASE_URL.split())

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    """Create database connection - supports both SQLite (local) and PostgreSQL (Supabase)"""
    if DATABASE_URL:
        parsed = urlparse(DATABASE_URL)
        if not parsed.hostname:
            raise ValueError("Invalid DATABASE_URL: hostname is missing or malformed")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=extras.RealDictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    return conn


def extract_returning_id(row):
    """Extract inserted id from tuple-like or dict-like RETURNING rows."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get("id")
    try:
        return row[0]
    except (KeyError, IndexError, TypeError):
        return None


def extract_from_pdf(file_data):
    """Extract course data from PDF bytes"""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_data))
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        return parse_course_data(text)
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None


def parse_course_data(text):
    """Parse extracted text into structured course data"""
    lines = [l.strip() for l in text.split("\n")]

    title = "Unknown"
    for line in lines:
        if (
            line
            and not line.startswith(
                (
                    "Instructor:",
                    "Location:",
                    "Course Type:",
                    "Cost:",
                    "Learning",
                    "Provided",
                    "Skills",
                    "Course",
                    "Class ID:",
                )
            )
            and "Instructor:" not in line
            and "Location:" not in line
        ):
            title = line
            break

    def find_line_containing(search_text):
        for i, line in enumerate(lines):
            if search_text in line:
                return i
        return -1

    def extract_value_with_embedded_label(label_text, embedded_label, next_line_label):
        try:
            idx = lines.index(label_text)
            if idx + 1 < len(lines):
                value_line = lines[idx + 1]
                if embedded_label in value_line:
                    return value_line.replace(embedded_label, "").strip()
                return value_line
            return None
        except ValueError:
            return None

    def extract_value_after_embedded_label(embedded_label):
        idx = find_line_containing(embedded_label)
        if idx >= 0 and idx + 1 < len(lines):
            return lines[idx + 1]
        return None

    instructor = extract_value_with_embedded_label(
        "Instructor:", "Location:", "Location:"
    )
    location = extract_value_after_embedded_label("Location:")
    course_type = extract_value_with_embedded_label("Course Type:", "Cost:", "Cost:")
    cost = extract_value_after_embedded_label("Cost:")

    class_id_match = re.search(r"Class ID:\s*(CLASS_\d+)", text)
    class_id = class_id_match.group(1) if class_id_match else None

    objectives_match = re.search(
        r"Learning Objectives\s*\n(.+?)Provided Materials", text, re.DOTALL
    )
    learning_objectives = (
        objectives_match.group(1).strip() if objectives_match else None
    )

    materials_match = re.search(
        r"Provided Materials\s*\n(.+?)Skills Developed", text, re.DOTALL
    )
    provided_materials = materials_match.group(1).strip() if materials_match else None

    skills_match = re.search(
        r"Skills Developed\s*\n(.+?)Course Description", text, re.DOTALL
    )
    skills = skills_match.group(1).strip() if skills_match else None

    description_match = re.search(
        r"Course Description\s*\n(.+?)Class ID:", text, re.DOTALL
    )
    description = description_match.group(1).strip() if description_match else None

    return {
        "class_id": class_id,
        "title": title,
        "instructor": instructor,
        "location": location,
        "course_type": course_type,
        "cost": cost,
        "learning_objectives": learning_objectives,
        "provided_materials": provided_materials,
        "skills": skills,
        "description": description,
    }


@app.route("/")
def index():
    """Serve the HTML interface"""
    return render_template("index.html")


@app.route("/api/courses", methods=["GET"])
def get_courses():
    """Get all courses with optional filtering"""
    search = request.args.get("search", "")
    location = request.args.get("location", "")
    course_type = request.args.get("course_type", "")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        use_postgres = bool(DATABASE_URL)
        placeholder = "%s" if use_postgres else "?"

        query = """
            SELECT id, class_id, title, instructor, location, course_type, cost, 
                   skills, filename, pdf_url, created_at, updated_at
            FROM courses
            WHERE 1=1
        """
        params = []

        if search:
            if use_postgres:
                query += (
                    " AND (title ILIKE %s OR class_id ILIKE %s OR description ILIKE %s)"
                )
            else:
                query += " AND (title LIKE ? OR class_id LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if location:
            query += f" AND location LIKE {placeholder}"
            params.append(f"%{location}%")

        if course_type:
            query += f" AND course_type LIKE {placeholder}"
            params.append(f"%{course_type}%")

        query += " ORDER BY class_id"

        cursor.execute(query, params)
        courses = list(cursor.fetchall())

        return jsonify({"count": len(courses), "courses": courses})
    except Exception as e:
        app.logger.exception("Failed to fetch courses")
        return jsonify({"error": f"Failed to fetch courses: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    """Get a single course by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()

    use_postgres = bool(DATABASE_URL)
    placeholder = "%s" if use_postgres else "?"

    cursor.execute(f"SELECT * FROM courses WHERE id = {placeholder}", (course_id,))

    course = cursor.fetchone()
    conn.close()

    if course:
        return jsonify(dict(course))
    else:
        return jsonify({"error": "Course not found"}), 404


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


@app.route("/api/upload", methods=["POST"])
def upload_pdf():
    """Upload a PDF, process it through the pipeline, and store in database"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    file_data = file.read()
    filename = secure_filename(file.filename) if file.filename else "unknown.pdf"

    unique_filename = f"{uuid.uuid4().hex}_{filename}"

    course_data = extract_from_pdf(file_data)

    if not course_data:
        return jsonify({"error": "Failed to extract data from PDF"}), 400

    course_data["filename"] = unique_filename

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if DATABASE_URL:
            cursor.execute(
                """
                INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename, pdf_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    course_data.get("class_id"),
                    course_data.get("title"),
                    course_data.get("instructor"),
                    course_data.get("location"),
                    course_data.get("course_type"),
                    course_data.get("cost"),
                    course_data.get("learning_objectives"),
                    course_data.get("provided_materials"),
                    course_data.get("skills"),
                    course_data.get("description"),
                    course_data.get("filename"),
                    course_data.get("pdf_url"),
                ),
            )
            course_id = extract_returning_id(cursor.fetchone())
        else:
            cursor.execute(
                """
                INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename, pdf_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    course_data.get("class_id"),
                    course_data.get("title"),
                    course_data.get("instructor"),
                    course_data.get("location"),
                    course_data.get("course_type"),
                    course_data.get("cost"),
                    course_data.get("learning_objectives"),
                    course_data.get("provided_materials"),
                    course_data.get("skills"),
                    course_data.get("description"),
                    course_data.get("filename"),
                    course_data.get("pdf_url"),
                ),
            )
            course_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify(
            {
                "id": course_id,
                "message": "Course created",
                "data": course_data,
            }
        ), 201
    except Exception as e:
        app.logger.exception("Failed to create course from upload")
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses", methods=["POST"])
def create_course():
    """Create a new course manually"""
    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()
    use_postgres = bool(DATABASE_URL)

    class_id = (data.get("class_id") or "").strip()
    if class_id:
        filename = f"{class_id}_{uuid.uuid4().hex[:8]}.pdf"
    else:
        filename = f"manual_{uuid.uuid4().hex}.pdf"

    try:
        if use_postgres:
            cursor.execute(
                """
                INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    class_id or None,
                    data.get("title"),
                    data.get("instructor"),
                    data.get("location"),
                    data.get("course_type"),
                    data.get("cost"),
                    data.get("learning_objectives"),
                    data.get("provided_materials"),
                    data.get("skills"),
                    data.get("description"),
                    filename,
                ),
            )
            course_id = extract_returning_id(cursor.fetchone())
        else:
            cursor.execute(
                """
                INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    class_id or None,
                    data.get("title"),
                    data.get("instructor"),
                    data.get("location"),
                    data.get("course_type"),
                    data.get("cost"),
                    data.get("learning_objectives"),
                    data.get("provided_materials"),
                    data.get("skills"),
                    data.get("description"),
                    filename,
                ),
            )
            course_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({"id": course_id, "message": "Course created"}), 201
    except Exception as e:
        app.logger.exception("Failed to create manual course")
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    """Update an existing course"""
    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE courses SET
                class_id = %s,
                title = %s,
                instructor = %s,
                location = %s,
                course_type = %s,
                cost = %s,
                learning_objectives = %s,
                provided_materials = %s,
                skills = %s,
                description = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """,
            (
                data.get("class_id"),
                data.get("title"),
                data.get("instructor"),
                data.get("location"),
                data.get("course_type"),
                data.get("cost"),
                data.get("learning_objectives"),
                data.get("provided_materials"),
                data.get("skills"),
                data.get("description"),
                course_id,
            ),
        )
        conn.commit()
        conn.close()

        return jsonify({"message": "Course updated"}), 200
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """Delete a course"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        use_postgres = bool(DATABASE_URL)
        placeholder = "%s" if use_postgres else "?"

        cursor.execute(f"SELECT id FROM courses WHERE id = {placeholder}", (course_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Course not found"}), 404

        cursor.execute(f"DELETE FROM courses WHERE id = {placeholder}", (course_id,))
        conn.commit()
        conn.close()

        return jsonify({"message": "Course deleted"}), 200
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
