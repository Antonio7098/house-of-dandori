import io
import os
import re
import uuid
import json
from typing import Optional

import PyPDF2
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from src.core.config import ALLOWED_EXTENSIONS
from src.core.utils import to_json, parse_json_fields
from src.models.database import get_db_connection, extract_returning_id

courses_bp = Blueprint("courses", __name__)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_from_pdf(file_data, filename=None):
    from src.models.extractor import CourseExtractor

    extractor = CourseExtractor()
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_data))
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return extractor._parse_course_data(text, filename)
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None


@courses_bp.route("/api/courses", methods=["GET"])
def get_courses():
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

        db_url = os.environ.get("DATABASE_URL")
        use_postgres = bool(db_url)
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
        if isinstance(count_result, (tuple, list)):
            total = count_result[0]
        elif hasattr(count_result, "keys"):
            total = (
                count_result["count"]
                if "count" in count_result.keys()
                else count_result[0]
            )
        else:
            total = count_result[0]

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
        return jsonify({"error": f"Failed to fetch courses: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@courses_bp.route("/api/courses/bulk", methods=["POST"])
def get_courses_bulk():
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
        use_postgres = bool(os.environ.get("DATABASE_URL"))
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
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@courses_bp.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    use_postgres = bool(os.environ.get("DATABASE_URL"))
    placeholder = "%s" if use_postgres else "?"

    cursor.execute(f"SELECT * FROM courses WHERE id = {placeholder}", (course_id,))
    course = cursor.fetchone()
    conn.close()

    if course:
        return jsonify(parse_json_fields(course))
    return jsonify({"error": "Course not found"}), 404


@courses_bp.route("/api/courses", methods=["POST"])
def create_course():
    data = request.json
    use_postgres = bool(os.environ.get("DATABASE_URL"))

    conn = get_db_connection()
    cursor = conn.cursor()

    class_id = (data.get("class_id") or "").strip()
    if class_id:
        filename = f"{class_id}_{uuid.uuid4().hex[:8]}.pdf"
    else:
        filename = f"manual_{uuid.uuid4().hex}.pdf"

    try:
        if use_postgres:
            cursor.execute(
                """INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id""",
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
                """INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        conn.close()
        return jsonify({"error": str(e)}), 400


@courses_bp.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    data = request.json
    use_postgres = bool(os.environ.get("DATABASE_URL"))
    placeholder = "%s" if use_postgres else "?"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""UPDATE courses SET
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
            WHERE id = {placeholder}""",
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


@courses_bp.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    use_postgres = bool(os.environ.get("DATABASE_URL"))
    placeholder = "%s" if use_postgres else "?"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
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


@courses_bp.route("/api/upload", methods=["POST"])
def upload_pdf():
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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if os.environ.get("DATABASE_URL"):
            cursor.execute(
                """INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename, pdf_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id""",
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
                """INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename, pdf_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            {"id": course_id, "message": "Course created", "data": course_data}
        ), 201
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400


def process_single_pdf(file, use_postgres):
    """Process a single PDF file and return course data."""
    file_data = file.read()
    filename = secure_filename(file.filename) if file.filename else "unknown.pdf"
    unique_filename = f"{uuid.uuid4().hex}_{filename}"

    course_data = extract_from_pdf(file_data, filename)
    if not course_data:
        return None

    course_data["filename"] = unique_filename
    if not course_data.get("class_id"):
        course_data["class_id"] = f"CLASS_{uuid.uuid4().hex[:8].upper()}"

    return insert_course(course_data, use_postgres)


def insert_course(course_data, use_postgres):
    """Insert course data into database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if use_postgres:
            cursor.execute(
                """INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename, pdf_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id""",
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
                """INSERT INTO courses (
                    class_id, title, instructor, location, course_type, cost,
                    learning_objectives, provided_materials, skills, description, filename, pdf_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        return {"id": course_id, "message": "Course created", "data": course_data}
    except Exception as e:
        conn.close()
        raise e


@courses_bp.route("/api/upload/batch", methods=["POST"])
def upload_batch():
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files selected"}), 400

    use_postgres = bool(os.environ.get("DATABASE_URL"))
    results = []
    successful = 0
    failed = 0

    for i, file in enumerate(files):
        if not allowed_file(file.filename):
            results.append(
                {
                    "filename": file.filename,
                    "success": False,
                    "error": "File type not allowed",
                }
            )
            failed += 1
            continue

        try:
            result = process_single_pdf(file, use_postgres)
            if result:
                results.append(
                    {
                        "filename": file.filename,
                        "success": True,
                        "course_id": result["id"],
                        "title": result["data"].get("title"),
                    }
                )
                successful += 1
            else:
                results.append(
                    {
                        "filename": file.filename,
                        "success": False,
                        "error": "Failed to extract data from PDF",
                    }
                )
                failed += 1
        except Exception as e:
            results.append(
                {"filename": file.filename, "success": False, "error": str(e)}
            )
            failed += 1

    return jsonify(
        {
            "total": len(files),
            "successful": successful,
            "failed": failed,
            "results": results,
        }
    ), 200
