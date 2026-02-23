import os
import re
import json
from pathlib import Path
from typing import Dict, Optional

import PyPDF2

from src.core.utils import clean_location, text_to_list
from src.models.database import DatabaseManager

__all__ = ["CourseExtractor", "DatabaseManager"]


class CourseExtractor:
    def extract_from_pdf(self, pdf_path: str) -> Optional[Dict]:
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
        lines = [l.strip() for l in text.split("\n")]

        filename = Path(pdf_path).name
        filename_match = re.search(r"class_(\d+)", filename, re.IGNORECASE)
        class_id = f"CLASS_{filename_match.group(1)}" if filename_match else None

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
            "filename": Path(pdf_path).name,
        }
