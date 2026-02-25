#!/usr/bin/env python3
"""Test script to identify problematic course in batch 9 (courses 161-180)"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.core.utils import parse_json_fields
from src.models.database import get_db_connection
from src.services.rag_service import get_rag_service

# Load environment variables
load_dotenv()

print("Testing batch 9 (courses 161-180) one by one...")
print("=" * 70)

# Get courses 161-180
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM courses LIMIT 20 OFFSET 160")
courses = [parse_json_fields(c) for c in cursor.fetchall()]
conn.close()

print(f"Found {len(courses)} courses to test\n")

# Get RAG service
rag = get_rag_service()

# Test each course individually
for i, course in enumerate(courses, start=161):
    try:
        print(f"Course {i} (ID: {course['id']}): {course.get('title', 'N/A')[:50]}...", end=" ")
        rag.index_courses([course])
        print("✅")
    except Exception as e:
        print(f"❌")
        print(f"  Error: {str(e)[:200]}")
        print(f"  Course data keys: {list(course.keys())}")
        print(f"  Problematic fields:")
        for key, value in course.items():
            if value is None:
                print(f"    - {key}: None")
            elif isinstance(value, str) and len(value) > 1000:
                print(f"    - {key}: Very long string ({len(value)} chars)")
            elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                print(f"    - {key}: Unusual type {type(value)}")
        print()

print("\n" + "=" * 70)
print("Test complete!")
