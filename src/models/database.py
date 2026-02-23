import os
import sqlite3
import json
from typing import Dict, Optional

import psycopg2
from psycopg2 import extras

from src.core.config import DATABASE_URL, DB_PATH
from src.core.utils import to_json


class DatabaseManager:
    def __init__(self, database_url: str = None, db_path: str = None):
        self.database_url = database_url or DATABASE_URL
        self.db_path = db_path or DB_PATH
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
                        to_json(course_data["learning_objectives"]),
                        to_json(course_data["provided_materials"]),
                        to_json(course_data["skills"]),
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
                        to_json(course_data["learning_objectives"]),
                        to_json(course_data["provided_materials"]),
                        to_json(course_data["skills"]),
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


def get_db_connection():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=extras.RealDictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    return conn


def extract_returning_id(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get("id")
    try:
        return row[0]
    except (KeyError, IndexError, TypeError):
        return None
