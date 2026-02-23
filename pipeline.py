#!/usr/bin/env python3
"""
School of Dandori - Course Data Ingestion Pipeline
Extracts course information from PDFs and loads into database
"""

import os
import re
import sqlite3
import psycopg2
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

import PyPDF2


class CourseExtractor:
    """Extracts course data from PDF files"""

    def extract_from_pdf(self, pdf_path: str) -> Optional[Dict]:
        """Extract course information from a single PDF"""
        try:
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()

                return self._parse_course_data(text, pdf_path)
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return None

    def _parse_course_data(self, text: str, pdf_path: str) -> Dict:
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

        def extract_value_with_embedded_label(
            label_text, embedded_label, next_line_label
        ):
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
        course_type = extract_value_with_embedded_label(
            "Course Type:", "Cost:", "Cost:"
        )
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
        provided_materials = (
            materials_match.group(1).strip() if materials_match else None
        )

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
            "filename": Path(pdf_path).name,
        }


class DatabaseManager:
    """Manages database operations - supports SQLite and PostgreSQL"""

    def __init__(self, database_url: str = None, db_path: str = "courses.db"):
        self.database_url = database_url
        self.db_path = db_path
        self.conn = None

    def connect(self):
        if self.database_url:
            self.conn = psycopg2.connect(self.database_url)
        else:
            self.conn = sqlite3.connect(self.db_path)

    def initialize_schema(self):
        cursor = self.conn.cursor()

        if self.database_url:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id SERIAL PRIMARY KEY,
                    class_id TEXT,
                    title TEXT NOT NULL,
                    instructor TEXT,
                    location TEXT,
                    course_type TEXT,
                    cost TEXT,
                    learning_objectives TEXT,
                    provided_materials TEXT,
                    skills TEXT,
                    description TEXT,
                    filename TEXT NOT NULL UNIQUE,
                    pdf_url TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id TEXT,
                    title TEXT NOT NULL,
                    instructor TEXT,
                    location TEXT,
                    course_type TEXT,
                    cost TEXT,
                    learning_objectives TEXT,
                    provided_materials TEXT,
                    skills TEXT,
                    description TEXT,
                    filename TEXT NOT NULL UNIQUE,
                    pdf_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        self.conn.commit()

    def insert_course(self, course_data: Dict) -> bool:
        try:
            cursor = self.conn.cursor()

            if self.database_url:
                cursor.execute(
                    """
                    INSERT INTO courses (
                        class_id, title, instructor, location, course_type, cost,
                        learning_objectives, provided_materials, skills, description, filename
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(filename) DO UPDATE SET
                        class_id = EXCLUDED.class_id,
                        title = EXCLUDED.title,
                        instructor = EXCLUDED.instructor,
                        location = EXCLUDED.location,
                        course_type = EXCLUDED.course_type,
                        cost = EXCLUDED.cost,
                        learning_objectives = EXCLUDED.learning_objectives,
                        provided_materials = EXCLUDED.provided_materials,
                        skills = EXCLUDED.skills,
                        description = EXCLUDED.description,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        course_data["class_id"],
                        course_data["title"],
                        course_data["instructor"],
                        course_data["location"],
                        course_data["course_type"],
                        course_data["cost"],
                        course_data["learning_objectives"],
                        course_data["provided_materials"],
                        course_data["skills"],
                        course_data["description"],
                        course_data["filename"],
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO courses (
                        class_id, title, instructor, location, course_type, cost,
                        learning_objectives, provided_materials, skills, description, filename
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(filename) DO UPDATE SET
                        class_id = excluded.class_id,
                        title = excluded.title,
                        instructor = excluded.instructor,
                        location = excluded.location,
                        course_type = excluded.course_type,
                        cost = excluded.cost,
                        learning_objectives = excluded.learning_objectives,
                        provided_materials = excluded.provided_materials,
                        skills = excluded.skills,
                        description = excluded.description,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        course_data["class_id"],
                        course_data["title"],
                        course_data["instructor"],
                        course_data["location"],
                        course_data["course_type"],
                        course_data["cost"],
                        course_data["learning_objectives"],
                        course_data["provided_materials"],
                        course_data["skills"],
                        course_data["description"],
                        course_data["filename"],
                    ),
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting course: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    import sys

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        database_url = "".join(database_url.split())
    pdf_dir = sys.argv[1] if len(sys.argv) > 1 else "pdfs"

    print("Starting School of Dandori data ingestion pipeline...")

    db = DatabaseManager(database_url=database_url)
    db.connect()
    db.initialize_schema()
    print("✓ Database initialized")

    extractor = CourseExtractor()
    pdf_files = list(Path(pdf_dir).glob("*.pdf"))
    print(f"✓ Found {len(pdf_files)} course PDFs")

    success_count = 0
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        course_data = extractor.extract_from_pdf(str(pdf_path))

        if course_data and db.insert_course(course_data):
            success_count += 1
            print(f"  ✓ {course_data.get('title', 'Unknown')}")

    db.close()
    print(f"\n✓ Pipeline complete: {success_count}/{len(pdf_files)} courses ingested")
