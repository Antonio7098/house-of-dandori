#!/usr/bin/env python3
"""
School of Dandori - Course Data Ingestion Pipeline (Entry Point)
Extracts course information from PDFs and loads into database
"""

import sys
from pathlib import Path

from src.models.database import DatabaseManager
from src.models import CourseExtractor


def main(pdf_dir: str = "pdfs"):
    from src.core.config import DATABASE_URL

    print("Starting School of Dandori data ingestion pipeline...")

    db = DatabaseManager()
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


if __name__ == "__main__":
    pdf_dir = sys.argv[1] if len(sys.argv) > 1 else "pdfs"
    main(pdf_dir)
