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
import json
from urllib.parse import urlparse
from pathlib import Path
from typing import List, Optional
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

LOCATION_CLEANUP = {
    "Harrogate, UK": "Harrogate",
    "Oxford Botanical Gardens": "Oxford",
}


def clean_location(location: Optional[str]) -> Optional[str]:
    if not location:
        return location
    return LOCATION_CLEANUP.get(location, location)


def text_to_list(text: Optional[str]) -> Optional[List[str]]:
    if not text:
        return None
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        stripped = line.lstrip("•·-* ").strip()
        if stripped:
            items.append(stripped)
    return items if items else None


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


def extract_from_pdf(file_data, filename=None):
    """Extract course data from PDF bytes"""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_data))
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        return parse_course_data(text, filename)
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None


def parse_course_data(text, filename=None):
    """Parse extracted text into structured course data"""
    lines = [l.strip() for l in text.split("\n")]

    if filename:
        filename_match = re.search(r"class_(\d+)", filename, re.IGNORECASE)
        class_id = f"CLASS_{filename_match.group(1)}" if filename_match else None
    else:
        class_id = None

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

    objectives_match = re.search(
        r"Learning Objectives\s*\n(.+?)Provided Materials", text, re.DOTALL
    )
    learning_objectives = text_to_list(
        objectives_match.group(1).strip() if objectives_match else None
    )

    materials_match = re.search(
        r"Provided Materials\s*\n(.+?)Skills Developed", text, re.DOTALL
    )
    provided_materials = text_to_list(
        materials_match.group(1).strip() if materials_match else None
    )

    skills_match = re.search(
        r"Skills Developed\s*\n(.+?)Course Description", text, re.DOTALL
    )
    skills = text_to_list(skills_match.group(1).strip() if skills_match else None)

    description_match = re.search(
        r"Course Description\s*\n(.+?)Class ID:", text, re.DOTALL
    )
    description = description_match.group(1).strip() if description_match else None
    description = (
        " ".join(line.strip() for line in description.split("\n"))
        if description
        else None
    )

    return {
        "class_id": class_id,
        "title": title,
        "instructor": instructor,
        "location": clean_location(location),
        "course_type": course_type,
        "cost": cost,
        "learning_objectives": learning_objectives,
        "provided_materials": provided_materials,
        "skills": skills,
        "description": description,
    }


def parse_json_fields(course):
    """Parse JSON string fields back to lists"""
    if not course:
        return course
    json_fields = ["learning_objectives", "provided_materials", "skills"]
    result = dict(course) if not isinstance(course, dict) else course.copy()
    for field in json_fields:
        val = result.get(field)
        if val and isinstance(val, str):
            try:
                result[field] = json.loads(val)
            except json.JSONDecodeError:
                pass
    return result


@app.route("/")
def index():
    """Serve the HTML interface"""
    return render_template("index.html")


@app.route("/api/courses", methods=["GET"])
def get_courses():
    """Get all courses with optional filtering and pagination"""
    search = request.args.get("search", "")
    location = request.args.get("location", "")
    course_type = request.args.get("course_type", "")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    offset = (page - 1) * limit

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
        count_query = "SELECT COUNT(*) FROM courses WHERE 1=1"
        params = []
        count_params = []

        if search:
            if use_postgres:
                query += (
                    " AND (title ILIKE %s OR class_id ILIKE %s OR description ILIKE %s)"
                )
                count_query += (
                    " AND (title ILIKE %s OR class_id ILIKE %s OR description ILIKE %s)"
                )
            else:
                query += " AND (title LIKE ? OR class_id LIKE ? OR description LIKE ?)"
                count_query += (
                    " AND (title LIKE ? OR class_id LIKE ? OR description LIKE ?)"
                )
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            count_params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if location:
            query += f" AND location LIKE {placeholder}"
            count_query += f" AND location LIKE {placeholder}"
            params.append(f"%{location}%")
            count_params.append(f"%{location}%")

        if course_type:
            query += f" AND course_type LIKE {placeholder}"
            count_query += f" AND course_type LIKE {placeholder}"
            params.append(f"%{course_type}%")
            count_params.append(f"%{course_type}%")

        cursor.execute(count_query, count_params)
        count_result = cursor.fetchone()
        total = (
            count_result[0]
            if isinstance(count_result, (tuple, list))
            else count_result["count"]
        )

        query += f" ORDER BY class_id LIMIT {placeholder} OFFSET {placeholder}"
        params.extend([limit, offset])

        cursor.execute(query, params)
        courses = [parse_json_fields(c) for c in cursor.fetchall()]

        return jsonify(
            {
                "count": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit,
                "courses": courses,
            }
        )
    except Exception as e:
        app.logger.exception("Failed to fetch courses")
        return jsonify({"error": f"Failed to fetch courses: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/courses/bulk", methods=["POST"])
def get_courses_bulk():
    """Get multiple courses by IDs"""
    data = request.get_json()
    if not data or not data.get("ids"):
        return jsonify({"error": "ids array is required"}), 400

    course_ids = data["ids"]
    if not isinstance(course_ids, list):
        return jsonify({"error": "ids must be an array"}), 400

    if len(course_ids) > 100:
        return jsonify({"error": "Maximum 100 IDs allowed"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        use_postgres = bool(DATABASE_URL)
        placeholder = "%s" if use_postgres else "?"

        placeholders = ",".join([placeholder] * len(course_ids))
        cursor.execute(
            f"SELECT * FROM courses WHERE id IN ({placeholders})", course_ids
        )
        courses = [parse_json_fields(c) for c in cursor.fetchall()]

        course_map = {c["id"]: c for c in courses}
        ordered = [course_map[cid] for cid in course_ids if cid in course_map]

        return jsonify({"courses": ordered})
    except Exception as e:
        app.logger.exception("Failed to fetch bulk courses")
        return jsonify({"error": str(e)}), 500
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
        return jsonify(parse_json_fields(course))
    else:
        return jsonify({"error": "Course not found"}), 404


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


rag_service = None


def get_rag_service():
    global rag_service
    if rag_service is None:
        from rag_service import get_rag_service as _get_rag

        provider = request.args.get("provider")
        rag_service = _get_rag(provider)
    return rag_service


@app.route("/api/search", methods=["GET"])
def semantic_search():
    """Semantic search using vector store"""
    query = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("n", 10))
    offset = (page - 1) * limit

    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    try:
        rag = get_rag_service()
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
        use_postgres = bool(DATABASE_URL)
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
        app.logger.exception("Semantic search failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/index", methods=["POST"])
def index_courses():
    """Index all courses into the vector store"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

        if not courses:
            return jsonify({"message": "No courses to index", "count": 0})

        rag = get_rag_service()
        rag.index_courses(courses)

        return jsonify({"message": "Courses indexed", "count": len(courses)})

    except Exception as e:
        app.logger.exception("Indexing failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/reindex", methods=["POST"])
def reindex_courses():
    """Wipe vector store and re-index all courses from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

        if not courses:
            return jsonify({"message": "No courses to index", "count": 0})

        rag = get_rag_service()

        chunks = rag.build_chunks(courses)
        if chunks:
            rag.vector_store.delete([c["id"] for c in chunks])

        rag.index_courses(courses)

        return jsonify(
            {"message": "Vector store wiped and re-indexed", "count": len(courses)}
        )

    except Exception as e:
        app.logger.exception("Reindex failed")
        return jsonify({"error": str(e)}), 500


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

    course_data = extract_from_pdf(file_data, filename)

    if not course_data:
        return jsonify({"error": "Failed to extract data from PDF"}), 400

    course_data["filename"] = unique_filename

    if not course_data.get("class_id"):
        course_data["class_id"] = f"CLASS_{uuid.uuid4().hex[:8].upper()}"

    def to_json(val):
        return json.dumps(val) if val is not None else None

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
                    to_json(course_data.get("learning_objectives")),
                    to_json(course_data.get("provided_materials")),
                    to_json(course_data.get("skills")),
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
                    to_json(course_data.get("learning_objectives")),
                    to_json(course_data.get("provided_materials")),
                    to_json(course_data.get("skills")),
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

    def to_json(val):
        return json.dumps(val) if val is not None else None

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
                    to_json(data.get("learning_objectives")),
                    to_json(data.get("provided_materials")),
                    to_json(data.get("skills")),
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
                    to_json(data.get("learning_objectives")),
                    to_json(data.get("provided_materials")),
                    to_json(data.get("skills")),
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
    use_postgres = bool(DATABASE_URL)
    placeholder = "%s" if use_postgres else "?"

    def to_json(val):
        return json.dumps(val) if val is not None else None

    try:
        cursor.execute(
            f"""
            UPDATE courses SET
                class_id = {placeholder},
                title = {placeholder},
                instructor = {placeholder},
                location = {placeholder},
                course_type = {placeholder},
                cost = {placeholder},
                learning_objectives = {placeholder},
                provided_materials = {placeholder},
                skills = {placeholder},
                description = {placeholder},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {placeholder}
        """,
            (
                data.get("class_id"),
                data.get("title"),
                data.get("instructor"),
                data.get("location"),
                data.get("course_type"),
                data.get("cost"),
                to_json(data.get("learning_objectives")),
                to_json(data.get("provided_materials")),
                to_json(data.get("skills")),
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


def reindex_on_startup():
    """Reindex courses on startup"""
    try:
        from rag_service import get_rag_service

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses")
        courses = [parse_json_fields(c) for c in cursor.fetchall()]
        conn.close()

        if courses:
            rag = get_rag_service()
            print(f"Indexing {len(courses)} courses on startup...")
            rag.index_courses(courses)
            print(f"Indexed {len(courses)} courses")
    except Exception as e:
        print(f"Startup indexing failed: {e}")


if __name__ == "__main__":
    reindex_on_startup()
    app.run(host="0.0.0.0", port=5000, debug=True)
